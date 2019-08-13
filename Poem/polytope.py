#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Computations for polytopes."""

import subprocess
from multiprocessing import Pool, cpu_count
from scipy.optimize import linprog
import scipy
import numpy as np
import cvxpy as cvx
import Poem.aux as aux

def dwarfed_cube(n, scale = 2):
	"""Return the vertices of a scaled dwarved cube in given dimension."""
	call = 'print %d*dwarfed_cube(%d)->VERTICES;' % (scale, n)
	res = subprocess.check_output(['polymake',call], universal_newlines=True)
	points = np.array([[coord for coord in vertex.split(' ')] for vertex in res.splitlines()], dtype = np.int)
	return points.T[1:,:]

def interior_points(A, strict = True):
	"""Compute and list all interior points of the polytope given by matrix A."""
	polytope = 'declare $p = new Polytope(POINTS=>' + str(A.T.tolist()) + ');'
	if strict:
		points_call = 'print $p->INTERIOR_LATTICE_POINTS;'
	else:
		points_call = 'print $p->LATTICE_POINTS;'
	res = subprocess.check_output(['polymake',polytope + points_call], universal_newlines=True)
	return [[int(coord) for coord in vertex.split(' ')] for vertex in res.splitlines()]

def number_interior_points(A, strict = True):
	"""Compute number of interior points of the polytope given by matrix A."""
	polytope = 'declare $p = new Polytope(POINTS=>' + str(A.T.tolist()) + ');'
	number_call = 'prefer_now "libnormaliz";'
	if strict:
		number_call += 'print $p->N_INTERIOR_LATTICE_POINTS;'
	else:
		number_call += 'print $p->N_LATTICE_POINTS;'
	return int(subprocess.check_output(['polymake',polytope + number_call]))

def _get_inner_points(A, U_index, T_index):
	"""Compute which of the points lie in the interior.

	Call:
		Indices = _get_inner_points(A, U_index, T_index)
	Input:
		A: an (`m` x `n`)-matrix of non-negative integers
		U_index: iterable of column-indices, marking the interior points U
		T_index: list of column-indices, marking `m + 1` outer points T
	Output:
		Indices: T_index, expanded by the indices of U, which lie (strictly) inside T
	"""
	AA = A[:,T_index]
	Q,R = np.linalg.qr(AA)
	for ui in U_index:
		u = A[:,ui]
		x = scipy.linalg.solve_triangular(R, np.dot(Q.T, u))
		if all(x <= 1 - aux.EPSILON) and all(x >= aux.EPSILON) and all(abs(np.dot(AA,x) - u) < aux.EPSILON):
			T_index.append(ui)
	return T_index

def is_in_convex_hull(arg):
	"""Check whether v lies in the convex hull of point set A, using scipy."""
	A,v = arg
	res = linprog(np.zeros(A.shape[1]),A_eq = A,b_eq = v)
	return res['success']

def is_in_convex_hull_cvxpy(arg, exact = False):
	"""Check whether v lies in the convex hull of point set A, using cvxpy."""
	A,v = arg
	if exact:
		res = aux.LP_solve_exact(A,v)
		return res is not None
	else:
		lamb = cvx.Variable(A.shape[1])
		prob = cvx.Problem(cvx.Minimize(0), [A*lamb == v, lamb >= 0])
		prob.solve(solver = cvx.ECOS)
		return prob.status == 'optimal'

def convex_hull_LP_serial(A, exact = False):
	"""Compute the convex hull of a point set A with LPs.
	
	In contrast to convex_hull_LP() this function works in a single thread.

	Call:
		indices = convex_hull_LP_serial(A)
	Input:
		A: an (`m` x `n`)-matrix of non-negative integers
	Output:
		indices: list of indices, telling which columns of A form the convex hull
	"""
	return [i for i in range(A.shape[1]) if not is_in_convex_hull_cvxpy((np.delete(A,i,axis=1),A[:,i]), exact = exact)]

def convex_hull_LP(A):
	"""Compute the convex hull of a point set A with LPs.
	
	This function calls a new thread for each point, which creates a large overhead.

	Call:
		indices = convex_hull_LP(A)
	Input:
		A: an (`m` x `n`)-matrix of non-negative integers
	Output:
		indices: list of indices, telling which columns of A form the convex hull
	"""
	pool = Pool(processes = cpu_count())
	res = pool.map(is_in_convex_hull, [(np.delete(A,i,axis=1),A[:,i]) for i in range(A.shape[1])])
	pool.close()
	pool.join()
	return [i for i in range(A.shape[1]) if not res[i]]

convex_hull = convex_hull_LP_serial

if __name__ == "__main__":
	pass