from glayout import MappedPDK, sky130,gf180,ihp130
from glayout import nmos, pmos, tapring,via_stack


from gdsfactory.cell import cell
from gdsfactory.component import Component

from glayout.spice.netlist import Netlist
from glayout.routing import c_route,L_route,straight_route

from glayout.util.comp_utils import evaluate_bbox, prec_center, align_comp_to_port, movex, movey
from glayout.util.snap_to_grid import component_snap_to_grid
from glayout.util.port_utils import rename_ports_by_orientation
from glayout.util.port_utils import add_ports_perimeter
from gdsfactory.components import text_freetype, rectangle
from typing import Optional, Union 
import time

def add_tg_labels(tg_in: Component,
                        pdk: MappedPDK
                        ) -> Component:
	
    tg_in.unlock()
    
    # list that will contain all port/comp info
    move_info = list()
    # create labels and append to info list
    # vin
    vinlabel = rectangle(layer=pdk.get_glayer("met2_pin"),size=(0.27,0.27),centered=True).copy()
    vinlabel.add_label(text="VIN",layer=pdk.get_glayer("met2_label"))
    move_info.append((vinlabel,tg_in.ports["N_multiplier_0_source_E"],None))
    
    # vout
    voutlabel = rectangle(layer=pdk.get_glayer("met2_pin"),size=(0.27,0.27),centered=True).copy()
    voutlabel.add_label(text="VOUT",layer=pdk.get_glayer("met2_label"))
    move_info.append((voutlabel,tg_in.ports["P_multiplier_0_drain_W"],None))

    # sel
    voutlabel = rectangle(layer=pdk.get_glayer("met2_pin"),size=(0.27,0.27),centered=True).copy()
    voutlabel.add_label(text="VOUT",layer=pdk.get_glayer("met2_label"))
    move_info.append((voutlabel,tg_in.ports["P_multiplier_0_drain_W"],None))
    
    # vdd
    vcclabel = rectangle(layer=pdk.get_glayer("met2_pin"),size=(0.5,0.5),centered=True).copy()
    vcclabel.add_label(text="VCC",layer=pdk.get_glayer("met2_label"))
    move_info.append((vcclabel,tg_in.ports["P_tie_S_top_met_S"],None))
    
    # vss
    vsslabel = rectangle(layer=pdk.get_glayer("met2_pin"),size=(0.5,0.5),centered=True).copy()
    vsslabel.add_label(text="VSS",layer=pdk.get_glayer("met2_label"))
    move_info.append((vsslabel,tg_in.ports["N_tie_S_top_met_N"], None))


    # move everything to position
    for comp, prt, alignment in move_info:
        alignment = ('c','b') if alignment is None else alignment
        compref = align_comp_to_port(comp, prt, alignment=alignment)
        tg_in.add(compref)
    return tg_in.flatten() 


# def tg_netlist(nfet: Component, pfet: Component) -> Netlist:

#          netlist = Netlist(circuit_name='Transmission_Gate', nodes=['VIN', 'VSS', 'VOUT', 'VCC', 'VGP', 'VGN'])
#          netlist.connect_netlist(nfet.info['netlist'], [('D', 'VOUT'), ('G', 'VGN'), ('S', 'VIN'), ('B', 'VSS')])
#          netlist.connect_netlist(pfet.info['netlist'], [('D', 'VOUT'), ('G', 'VGP'), ('S', 'VIN'), ('B', 'VCC')])

#          return netlist

# @cell
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
        tie_layers: tuple[str,str] = ("met2","met1"),
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
    viam2m3 = via_stack(pdk, "met2", "met3", centered=True)    
    spacing = pdk.util_max_metal_seperation() + 1
    # fet_P_ref.movey(pfet_ref.center[1])
    # fet_P_ref.movex(pfet_ref.xmax + evaluate_bbox(fet_P)[0]/2 + spacing)

    #two fets
    nfet = nmos(pdk, width=width[0], fingers=fingers[0], multipliers=multipliers[0], with_dummy=True, with_dnwell=False,  with_substrate_tap=False, length=length[0], **kwargs)
    pfet = pmos(pdk, width=width[1], fingers=fingers[1], multipliers=multipliers[1], with_dummy=True, with_substrate_tap=False, length=length[1], **kwargs)
    nfet_ref = top_level << nfet
    pfet_ref = top_level << pfet 
    pfet_ref = rename_ports_by_orientation(pfet_ref.mirror_y())

    #Relative move
    pfet_ref.movey(nfet_ref.ymax + evaluate_bbox(pfet_ref)[1]/2 + pdk.util_max_metal_seperation())

    drain_via = top_level << viam2m3
    drain_via.move(nfet_ref.ports["multiplier_0_drain_W"].center).movex( (nfet_ref.xmax + evaluate_bbox(nfet)[0]/2 ))
    top_level << straight_route(pdk, nfet_ref.ports["multiplier_0_drain_W"], drain_via.ports["bottom_met_E"])
    source_via = top_level << viam2m3
    source_via.move(pfet_ref.ports["multiplier_0_source_E"].center).movex((pfet_ref.xmax + evaluate_bbox(pfet)[0]/2 ))
    top_level << straight_route(pdk, pfet_ref.ports["multiplier_0_source_E"], source_via.ports["bottom_met_W"])
    gate_via = top_level << viam2m3
    gate_via.move(nfet_ref.ports["multiplier_0_gate_E"].center).movex( (nfet_ref.xmax + evaluate_bbox(nfet)[0]/2 ))
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
    Ifet_P = pmos(pdk, width=inv_width[0], fingers=inv_fingers[0], multipliers=inv_multipliers[0], with_dummy=True, with_substrate_tap=False, length=inv_length[0], tie_layers=tie_layers, **kwargs)
    Ifet_N = nmos(pdk, width=inv_width[1], fingers=inv_fingers[1], multipliers=inv_multipliers[1], with_dummy=True, with_substrate_tap=False, length=inv_length[1], tie_layers=tie_layers, with_dnwell=False, **kwargs)
    
    Ifet_P_ref = top_level << Ifet_P
    Ifet_N_ref = top_level << Ifet_N 

    # Rotate PMOS 180° so drain faces left (same side as NMOS drain) for direct routing
    #Ifet_P_ref = rename_ports_by_orientation(Ifet_P_ref.rotate(-180))
   
    # # Place Inverter to the right of the Transmission Gate
    Ifet_P_ref.movey(pfet_ref.center[1])
    Ifet_P_ref.movex(-(pfet_ref.xmax + evaluate_bbox(Ifet_P)[0]/2 ))
    
    Ifet_N_ref.movey(nfet_ref.center[1])
    Ifet_N_ref.movex(-(nfet_ref.xmax + evaluate_bbox(Ifet_N)[0]/2 ))
    
    top_level.add_ports(Ifet_N_ref.get_ports_list(), prefix="INN_")
    top_level.add_ports(Ifet_P_ref.get_ports_list(), prefix="INP_")

    gate_via_IP = top_level << viam2m3
    gate_via_IP.move(Ifet_P_ref.ports["multiplier_0_gate_S"].center)
    gate_via_IN = top_level << viam2m3
    gate_via_IN.move(Ifet_N_ref.ports["multiplier_0_gate_N"].center)

    ##########################33
    top_level << straight_route(pdk, nfet_ref.ports["multiplier_0_gate_E"],  Ifet_N_ref.ports["multiplier_0_gate_W"])
    top_level << straight_route(pdk, gate_via_IP.ports['top_met_S'],  gate_via_IN.ports['top_met_N'])
    ####################################
    top_level << c_route(pdk, Ifet_P_ref.ports["multiplier_0_drain_E"],  Ifet_N_ref.ports["multiplier_0_drain_E"])
    top_level << straight_route(pdk, pfet_ref.ports["multiplier_0_gate_W"],  Ifet_P_ref.ports["multiplier_0_drain_W"])



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
    # #############################################################
    # #substrate tap
    # if substrate_tap:
    #         substrate_tap_encloses =((evaluate_bbox(top_level)[0]+pdk.util_max_metal_seperation()), (evaluate_bbox(top_level)[1]+pdk.util_max_metal_seperation()))
    #         guardring_ref = top_level << tapring(
    #         pdk,
    #         enclosed_rectangle=substrate_tap_encloses,
    #         sdlayer="p+s/d",
    #         horizontal_glayer='met2',
    #         vertical_glayer='met1',
    #     )
    #         guardring_ref.move(nfet_ref.center).movey(evaluate_bbox(pfet_ref)[1]/2 + pdk.util_max_metal_seperation()/2).movex(evaluate_bbox(pfet_ref)[0]/2) 
    #         top_level.add_ports(guardring_ref.get_ports_list(),prefix="tap_")
    
    component = component_snap_to_grid(top_level) 
    #component.info['netlist'] = tg_netlist(nfet, pfet)


    return component


if __name__ == "__main__":
    comp = transmission_gate_with_inv(ihp130,width=(1,1),length=(0.15,0.15),fingers=(8,8),multipliers=(1,1),inv_width=(1,1),inv_length=(0.15,0.15),inv_fingers=(1,1),inv_multipliers=(1,1))
    comp.pprint_ports()
    #comp = add_tg_labels(comp,ihp130)
    comp.name = "tg_lv"
    comp.show()
    #print(comp.info['netlist'].generate_netlist())
    #print("...Running DRC...")
    #drc_result = ihp130.drc_magic(comp, "tg_lv")
    ## Klayout DRC
    #drc_result = gf180.drc(comp)\n
    
    time.sleep(5)
        
    #print("...Running LVS...")
    #lvs_res=ihp.lvs_netgen(comp, "TG")
    print("...Saving GDS...")
    comp.write_gds('out_TG.gds')
