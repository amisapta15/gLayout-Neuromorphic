from gdsfactory.typings import Component
from pydantic import validate_arguments
import gdsfactory as gf
import numpy as np

@validate_arguments
def component_snap_to_grid(comp: Component) -> Component:
	"""snaps all polygons and ports in component to grid
	comp = the component to snap to grid
	NOTE this function will flatten the component
	"""
	#return comp.flatten()
	# flatten the component then copy (snaps polygons and ports to grid)
	name = comp.name
	comp = comp.flatten().copy()
	comp.name = name
	return comp



def snap_array(arr, grid):
    return np.round(arr / grid).astype(np.int64) * grid


def np_component_snap_to_grid(comp, GRID=0.005):
    """Snap all polygons and ports in a component to grid."""
    name = comp.name
    c = comp.flatten().copy()
    c.name = name

    for poly in c.polygons:
        poly.points[:] = snap_array(poly.points, GRID)

    for port in c.ports.values():
        port.center = snap_array(port.center, GRID)

    for ref in c.references:
        ref.origin = snap_array(ref.origin, GRID)

    return c

@validate_arguments
def gf_component_snap_to_grid(comp: Component,GRID) -> Component:
	"""Snap polygons and ports in a component to grid.
	NOTE: still flattens hierarchy.
	"""
	name = comp.name
	c = comp.flatten().copy()
	c.name = name

	new_polys = []

	for poly in c.polygons:
		snapped = gf.snap.snap_to_grid(poly.points, GRID)
		layer = (poly.layer, poly.datatype)
		new_polys.append((snapped, layer))

	for poly in list(c.polygons):
		c.remove(poly)

	for pts, layer in new_polys:
		c.add_polygon(pts, layer=layer)

	for port in c.ports.values():
		port.center = gf.snap.snap_to_grid(port.center, GRID)

	c.name = name
	return c