from glayout import MappedPDK, sky130,gf180,ihp130
from glayout import nmos, pmos, tapring,via_stack

from glayout.placement.two_transistor_interdigitized import two_nfet_interdigitized, two_pfet_interdigitized
from glayout.placement.common_centroid_ab_ba import common_centroid_ab_ba
from gdsfactory import cell
from gdsfactory.component import Component
from gdsfactory.components import text_freetype, rectangle

from glayout.routing import c_route,L_route,straight_route
from glayout.spice.netlist import Netlist

from glayout.util.port_utils import add_ports_perimeter,rename_ports_by_orientation
from glayout.util.comp_utils import evaluate_bbox, prec_center, prec_ref_center, align_comp_to_port
from typing import Optional, Union 

import time

def add_cm_labels(cm_in: Component,
                pdk: MappedPDK 
                ) -> Component:
	
    cm_in.unlock()

    # list that will contain all port/comp info
    move_info = list()
    # create labels and append to info list
    # vss
    vsslabel = rectangle(layer=pdk.get_glayer("met2_pin"),size=(0.27,0.27),centered=True).copy()
    vsslabel.add_label(text="VSS",layer=pdk.get_glayer("met2_label"))
    move_info.append((vsslabel,cm_in.ports["fet_A_source_E"],None))
    
    # vref
    vreflabel = rectangle(layer=pdk.get_glayer("met2_pin"),size=(0.27,0.27),centered=True).copy()
    vreflabel.add_label(text="VREF",layer=pdk.get_glayer("met2_label"))
    move_info.append((vreflabel,cm_in.ports["fet_A_drain_N"],None))
    
    # vcopy
    vcopylabel = rectangle(layer=pdk.get_glayer("met2_pin"),size=(0.27,0.27),centered=True).copy()
    vcopylabel.add_label(text="VCOPY",layer=pdk.get_glayer("met2_label"))
    move_info.append((vcopylabel,cm_in.ports["fet_B_drain_N"],None))
    
    # VB
    vblabel = rectangle(layer=pdk.get_glayer("met2_pin"),size=(0.5,0.5),centered=True).copy()
    vblabel.add_label(text="VB",layer=pdk.get_glayer("met2_label"))
    move_info.append((vblabel,cm_in.ports["welltie_S_top_met_S"], None))
    
    # move everything to position
    for comp, prt, alignment in move_info:
        alignment = ('c','b') if alignment is None else alignment
        compref = align_comp_to_port(comp, prt, alignment=alignment)
        cm_in.add(compref)
    return cm_in.flatten() 

def current_mirror_netlist(
    pdk: MappedPDK, 
    width: float = 1,
    length: float = None,
    multipliers: int = 1, 
    with_dummy: bool = True,
    n_or_p_fet: Optional[str] = 'nfet',
    subckt_only: Optional[bool] = True,
) -> Netlist:
    if length is None:
        length = pdk.get_grule('poly')['min_width']
    if width is None:
        width = 3 
    mtop = multipliers if subckt_only else 1
    model = pdk.models[n_or_p_fet]
    
    source_netlist = """.subckt {circuit_name} {nodes} """ + f'l={length} w={width} m={mtop} ' + """
XA VREF VREF VSS VB {model} l={{l}} w={{w}} m={{m}}
XB VCOPY VREF VSS VB {model} l={{l}} w={{w}} m={{m}}"""
    if with_dummy:
        source_netlist += "\nXDUMMY VB VB VB VB {model} l={{l}} w={{w}} m={{2}}"
    source_netlist += "\n.ends {circuit_name}"

    instance_format = "X{name} {nodes} {circuit_name} l={length} w={width} m={mult}"
 
    return Netlist(
        circuit_name='CMIRROR',
        nodes=['VREF', 'VCOPY', 'VSS', 'VB'], 
        source_netlist=source_netlist,
        instance_format=instance_format,
        parameters={
            'model': model,
            'width': width,
            'length': length,   
            'mult': multipliers
        }
    )


@cell
def current_mirror(
    pdk: MappedPDK, 
    numcols: int = 3,
    device: str = 'nfet',
    with_dummy: Optional[bool] = True,
    with_substrate_tap: Optional[bool] = False,
    with_tie: Optional[bool] = True,
    tie_layers: tuple[str,str]=("met2","met1"),
    subckt_only: Optional[bool] = True,
    **kwargs
) -> Component:
    """An instantiable current mirror that returns a Component object. The current mirror is a two transistor interdigitized structure with a shorted source and gate. It can be instantiated with either nmos or pmos devices. It can also be instantiated with a dummy device, a substrate tap, and a tie layer, and is centered at the origin. Transistor A acts as the reference and Transistor B acts as the mirror fet

    Args:
        pdk (MappedPDK): the process design kit to use
        numcols (int): number of columns of the interdigitized fets
        device (str): nfet or pfet (can only interdigitize one at a time with this option)
        with_dummy (bool): True places dummies on either side of the interdigitized fets
        with_substrate_tap (bool): boolean to decide whether to place a substrate tapring
        with_tie (bool): boolean to decide whether to place a tapring for tielayer
        tie_layers (tuple[str,str], optional): the layers to use for the tie. Defaults to ("met2","met1").
        **kwargs: The keyword arguments are passed to the two_nfet_interdigitized or two_pfet_interdigitized functions and need to be valid arguments that can be accepted by the multiplier function

    Returns:
        Component: a current mirror component object
    """
    pdk.activate()
    top_level = Component("current mirror")
    # Define deviceA and deviceB as (factory, kwargs)
    deviceA = (nmos, {"pdk": pdk, "width": 1.0, "length": 0.15,"with_dnwell":False})  # NMOS params
    deviceB = (nmos, {"pdk": pdk, "width": 1.0, "length": 0.15,"with_dnwell":False})  # Identical for mirror

   # Place in "aba" pattern (single row: A-B-A)
    #trans_pair = two_transistor_place(pdk=pdk, pattern="ab ba", deviceA=deviceA, deviceB=deviceB)
    trans_pair = common_centroid_ab_ba(pdk)
    top_level.add_ports(trans_pair.get_ports_list(), prefix="fet_")

    top_level << trans_pair
    
    return top_level

if __name__ == "__main__":
    comp = current_mirror(ihp130)
    # comp.pprint_ports()
    #comp = add_cm_labels(comp,ihp130)
    comp.name = "CM"
    comp.show()
    #print(comp.info['netlist'].generate_netlist())
    #print("...Running DRC...")
    #drc_result = sky130.drc_magic(comp, "CM")
    ## Klayout DRC
    #drc_result = sky130.drc(comp)\n
    
    #time.sleep(5)
        
    #print("...Running LVS...")
    #lvs_res=sky130.lvs_netgen(comp, "CM")
    #print("...Saving GDS...")
    #comp.write_gds('out_CMirror.gds')
