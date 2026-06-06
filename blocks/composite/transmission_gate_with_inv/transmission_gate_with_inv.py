from glayout import MappedPDK, sky130,gf180,ihp130
from glayout import nmos, pmos, tapring,via_stack


from gdsfactory.cell import cell
from gdsfactory.component import Component

from glayout.spice.netlist import Netlist
from glayout.routing import c_route,L_route,straight_route

from glayout.util.comp_utils import evaluate_bbox, prec_center, align_comp_to_port, movex, movey
from glayout.util.snap_to_grid import component_snap_to_grid,gf_component_snap_to_grid,np_component_snap_to_grid
from glayout.util.port_utils import rename_ports_by_orientation
from glayout.util.port_utils import add_ports_perimeter
from gdsfactory.components import text_freetype, rectangle
from typing import Optional, Union 
import time
import numpy as np


def snap(v, grid=0.005):
    return np.round(v / grid).astype(np.int64) * grid


def snap_pt(pt, grid=0.005):
    #return tuple(np.round(np.array(pt) / grid) * grid)
    return np.round(pt / grid).astype(np.int64) * grid


def add_tg_labels(tg_in: Component,
                        pdk: MappedPDK
                        ) -> Component:
	
    tg_in.unlock()
    
    # list that will contain all port/comp info
    move_info = list()
    # create labels and append to info list
    # vin
    vinlabel = rectangle(layer=pdk.get_glayer("met3_pin"),size=(0.3,0.3),centered=True).copy()
    vinlabel.add_label(text="IN",layer=pdk.get_glayer("met3_label"))
    move_info.append((vinlabel,tg_in.ports["TG_IN_top_met_W"],None))
    
    # vout
    voutlabel = rectangle(layer=pdk.get_glayer("met3_pin"),size=(0.3,0.3),centered=True).copy()
    voutlabel.add_label(text="OUT",layer=pdk.get_glayer("met3_label"))
    move_info.append((voutlabel,tg_in.ports["TG_OUT_top_met_W"],None))

    # sel
    voutlabel = rectangle(layer=pdk.get_glayer("met3_pin"),size=(0.3,0.3),centered=True).copy()
    voutlabel.add_label(text="SEL",layer=pdk.get_glayer("met3_label"))
    move_info.append((voutlabel,tg_in.ports["TG_sel_top_met_W"],None))
    
    # move everything to position
    for comp, prt, alignment in move_info:
        alignment = ('c','b') if alignment is None else alignment
        compref = align_comp_to_port(comp, prt, alignment=alignment)
        tg_in.add(compref)
    return np_component_snap_to_grid(tg_in.flatten(), GRID=0.005) 


def  transmission_gate_with_inv(
        pdk: MappedPDK,
        width: tuple[float,float] = (1,1),
        length: tuple[float,float] = (0.15,0.15),
        fingers: tuple[int,int] = (2,2),
        multipliers: tuple[int,int] = (4,4),
        inv_width: tuple[float,float] = (1,1),
        inv_length: tuple[float,float] = (0.15,0.15),
        inv_fingers: tuple[int,int] = (2,2),
        inv_multipliers: tuple[int,int] = (4,4),
        substrate_tap: bool = False,
        **kwargs
        ) -> Component:
    """
    creates a transmission gate
    tuples are in (NMOS,PMOS) order
    **kwargs are any kwarg that is supported by nmos and pmos
    """
    pdk.activate()
    #top level component
    top_level = Component(name="transmission_gate")
    viam2m3 = via_stack(pdk, "met2", "met3", centered=True,fullbottom=True,fulltop=True)    
    spacing = pdk.util_max_metal_seperation() + 1
    # fet_P_ref.movey(pfet_ref.center[1])
    # fet_P_ref.movex(pfet_ref.xmax + evaluate_bbox(fet_P)[0]/2 + spacing)

    #two fets
    nfet = nmos(pdk, width=width[0], fingers=fingers[0], multipliers=multipliers[0], with_dummy=True,with_substrate_tap=False, with_dnwell=False, length=length[0], **kwargs)
    pfet = pmos(pdk, width=width[1], fingers=fingers[1], multipliers=multipliers[1], with_dummy=True, with_substrate_tap=False, length=length[1], **kwargs)
    nfet_ref = top_level << nfet
    pfet_ref = top_level << pfet 
    pfet_ref = rename_ports_by_orientation(pfet_ref.mirror_y())

    #Relative move
    pfet_ref.movey(snap(nfet_ref.ymax + evaluate_bbox(pfet_ref)[1]/2 + pdk.util_max_metal_seperation()))

    ## TG IN
    drain_via = top_level << viam2m3
    drain_via.move(snap_pt(nfet_ref.ports["multiplier_0_drain_W"].center)).movex(snap(top_level.xmax + evaluate_bbox(pfet)[0]/4 ))
    top_level << straight_route(pdk, nfet_ref.ports["multiplier_0_drain_W"], drain_via.ports["bottom_met_E"])
    
    ## TG OUT
    source_via = top_level << viam2m3
    source_via.move(snap_pt(pfet_ref.ports[f"multiplier_0_source_E"].center)).movex(snap(pfet_ref.xmax))
    top_level << straight_route(pdk, pfet_ref.ports["multiplier_0_source_E"], source_via.ports["bottom_met_E"])
    
    ## TG SEL
    gate_via = top_level << viam2m3
    gate_via.move(snap_pt(nfet_ref.ports[f"multiplier_0_gate_E"].center)).movex(snap(nfet_ref.xmax ))
    top_level << straight_route(pdk, nfet_ref.ports["multiplier_0_gate_E"], gate_via.ports["bottom_met_E"])
    
    #######################################################
    #Routing
    top_level << c_route(pdk, nfet_ref.ports["multiplier_0_source_E"], pfet_ref.ports["multiplier_0_source_E"])
    top_level << c_route(pdk, nfet_ref.ports["multiplier_0_drain_W"], pfet_ref.ports["multiplier_0_drain_W"], viaoffset=False)
    
    #Renaming Ports
    top_level.add_ports(nfet_ref.get_ports_list(), prefix="TGN_")
    top_level.add_ports(pfet_ref.get_ports_list(), prefix="TGP_")
    top_level.add_ports(drain_via.get_ports_list(), prefix="TG_IN_")
    top_level.add_ports(source_via.get_ports_list(), prefix="TG_OUT_")
    top_level.add_ports(gate_via.get_ports_list(), prefix="TG_sel_")

    # #################### Inverter    ####################
    Ifet_P = pmos(pdk, width=inv_width[0], fingers=inv_fingers[0], multipliers=inv_multipliers[0], with_dummy=True, with_substrate_tap=False, length=inv_length[0], **kwargs)
    Ifet_N = nmos(pdk, width=inv_width[1], fingers=inv_fingers[1], multipliers=inv_multipliers[1], with_dummy=True, with_substrate_tap=False, length=inv_length[1], with_dnwell=False, **kwargs)
    
    Ifet_P_ref = top_level << Ifet_P
    Ifet_N_ref = top_level << Ifet_N 

    # Rotate PMOS 180° so drain faces left (same side as NMOS drain) for direct routing
    #Ifet_P_ref = rename_ports_by_orientation(Ifet_P_ref.rotate(-180))
   
    # # Place Inverter to the right of the Transmission Gate
    Ifet_P_ref.movey(snap_pt(pfet_ref.center[1]))
    Ifet_P_ref.movex(snap(-(pfet_ref.xmax + evaluate_bbox(Ifet_P)[0]/2 )))
    
    Ifet_N_ref.movey(snap_pt(nfet_ref.center[1]))
    Ifet_N_ref.movex(snap(-(nfet_ref.xmax + evaluate_bbox(Ifet_N)[0]/2 )))
    
    top_level.add_ports(Ifet_N_ref.get_ports_list(), prefix="INN_")
    top_level.add_ports(Ifet_P_ref.get_ports_list(), prefix="INP_")

    #gate_via_IP = top_level << viam2m3
    #gate_via_IP.move(snap_pt(Ifet_P_ref.ports["multiplier_0_gate_S"].center))
    #gate_via_IN = top_level << viam2m3
    #gate_via_IN.move(snap_pt(Ifet_N_ref.ports["multiplier_0_gate_N"].center))

    ##########################33
    top_level << straight_route(pdk, nfet_ref.ports["multiplier_0_gate_E"],  Ifet_N_ref.ports["multiplier_0_gate_W"])
    #top_level << c_route(pdk, gate_via_IP.ports['top_met_W'],  gate_via_IN.ports['top_met_W'],viaoffset=False, e1glayer = 'met2',e2glayer = 'met2',cglayer = 'met3')
    top_level << c_route(pdk,Ifet_P_ref.ports["multiplier_0_gate_W"],Ifet_N_ref.ports["multiplier_0_gate_W"])
    top_level << c_route(pdk, Ifet_P_ref.ports["multiplier_0_drain_E"],  Ifet_N_ref.ports["multiplier_0_drain_E"])
    top_level << straight_route(pdk, pfet_ref.ports["multiplier_0_gate_W"],  Ifet_P_ref.ports["multiplier_0_drain_E"])



    # --- Connect INV PMOS source → VDD bulk tie ring ---
    try:
        top_level << straight_route(pdk,
            Ifet_P_ref.ports["multiplier_0_source_W"],
            Ifet_P_ref.ports["tie_W_top_met_W"],
            glayer1="met1", fullbottom=True)
    except:
        pass

    # --- Connect INV NMOS source → VSS bulk tie ring ---
    try:
        top_level << straight_route(pdk,
            Ifet_N_ref.ports["multiplier_0_source_W"],
            Ifet_N_ref.ports["tie_W_top_met_W"],
            glayer1="met1", fullbottom=True)
    except:
        pass
    #############################################################
    #substrate tap
    if substrate_tap:
            substrate_tap_encloses =((evaluate_bbox(top_level)[0]+pdk.util_max_metal_seperation()), (evaluate_bbox(top_level)[1]+pdk.util_max_metal_seperation()))
            guardring_ref = top_level << tapring(
            pdk,
            enclosed_rectangle=substrate_tap_encloses,
            sdlayer="p+s/d",
            horizontal_glayer='met2',
            vertical_glayer='met1',
        )
            guardring_ref.move(nfet_ref.center).movey(evaluate_bbox(pfet_ref)[1]/2 + pdk.util_max_metal_seperation()/2).movex(evaluate_bbox(pfet_ref)[0]/2) 
            top_level.add_ports(guardring_ref.get_ports_list(),prefix="tap_")
    
    component = np_component_snap_to_grid(top_level, GRID=0.005)
    return component


if __name__ == "__main__":
    comp = transmission_gate_with_inv(ihp130,width=(1,1),length=(0.15,0.15),fingers=(8,8),multipliers=(1,1),inv_width=(1,1),inv_length=(0.15,0.15),inv_fingers=(1,1),inv_multipliers=(1,1))
    #comp.pprint_ports()
    comp = add_tg_labels(comp,ihp130)
    comp.name = "tg_lv"
    comp.show()
        
    print("...Saving GDS...")
    comp.write_gds('out_final.gds')
