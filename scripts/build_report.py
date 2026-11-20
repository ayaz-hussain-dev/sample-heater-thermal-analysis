#!/usr/bin/env python3
"""Build the seven-page report from the checked metrics and existing figures."""
from __future__ import annotations

import json
from pathlib import Path
from xml.sax.saxutils import escape

import matplotlib
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph,
                               SimpleDocTemplate, Spacer, Table, TableStyle)

ROOT=Path(__file__).resolve().parents[1]
W,H=A4
NAVY=colors.HexColor("#243e52")
TEAL=colors.HexColor("#168273")
INK=colors.HexColor("#263744")
GREY=colors.HexColor("#52616c")
PALE=colors.HexColor("#f0f5f7")
RULE=colors.HexColor("#d5dfe5")
MARGIN=54
WIDTH=W-2*MARGIN


def main():
    m=json.loads((ROOT/"results/metrics.json").read_text())
    conf=json.loads((ROOT/"data/cases.json").read_text())
    g=m["geometry"];key=m["key"]
    fonts=Path(matplotlib.get_data_path())/"fonts/ttf"
    for name,file in [("Study","DejaVuSans.ttf"),("StudyBold","DejaVuSans-Bold.ttf"),
                      ("StudyItalic","DejaVuSans-Oblique.ttf")]:
        pdfmetrics.registerFont(TTFont(name,str(fonts/file)))
    pdfmetrics.registerFontFamily("Study",normal="Study",bold="StudyBold",italic="StudyItalic",boldItalic="StudyBold")
    styles={
        "title":ParagraphStyle("title",fontName="StudyBold",fontSize=27,leading=31,textColor=NAVY,spaceAfter=13),
        "h1":ParagraphStyle("h1",fontName="StudyBold",fontSize=20,leading=25,textColor=NAVY,spaceAfter=12),
        "h2":ParagraphStyle("h2",fontName="StudyBold",fontSize=11,leading=14,textColor=TEAL,spaceBefore=9,spaceAfter=5),
        "body":ParagraphStyle("body",fontName="Study",fontSize=9.2,leading=13.2,textColor=INK,spaceAfter=8),
        "small":ParagraphStyle("small",fontName="Study",fontSize=8,leading=11,textColor=GREY,spaceAfter=6),
        "cell":ParagraphStyle("cell",fontName="Study",fontSize=8,leading=10.4,textColor=INK),
        "th":ParagraphStyle("th",fontName="StudyBold",fontSize=8,leading=10.4,textColor=colors.white),
        "caption":ParagraphStyle("caption",fontName="Study",fontSize=7.5,leading=10,textColor=GREY,spaceAfter=6),
        "formula":ParagraphStyle("formula",fontName="Study",fontSize=9.2,leading=15,textColor=INK,leftIndent=12,spaceAfter=6),
        "label":ParagraphStyle("label",fontName="StudyBold",fontSize=9,leading=12,textColor=NAVY,alignment=TA_CENTER),
    }
    story=[]
    def p(text,style="body"):
        return Paragraph(text,styles[style])
    def add(text,style="body"):
        story.append(p(text,style))
    def title(n,text):
        add(f"AYAZ HUSSAIN  /  SAMPLE HEATER  /  {n:02d}","small")
        add(text,"h1")
    def table(data,widths=None):
        widths=widths or [WIDTH/len(data[0])]*len(data[0])
        cells=[[p(escape(str(x)),"th" if i==0 else "cell") for x in row] for i,row in enumerate(data)]
        t=Table(cells,colWidths=widths,hAlign="LEFT",repeatRows=1)
        t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),NAVY),
             ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,PALE]),
             ("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),8),
             ("RIGHTPADDING",(0,0),(-1,-1),8),("TOPPADDING",(0,0),(-1,-1),5),
             ("BOTTOMPADDING",(0,0),(-1,-1),5),
             ("LINEBELOW",(0,-1),(-1,-1),.45,RULE)]))
        story.append(t);story.append(Spacer(1,7))
    def image(rel,width=WIDTH):
        path=ROOT/rel
        with PILImage.open(path) as im:ratio=im.height/im.width
        return Image(str(path),width=width,height=width*ratio)
    def fig(rel,caption,width=WIDTH):
        story.append(image(rel,width));add(caption,"caption")
    def pair(rel_a,rel_b,caption):
        width=(WIDTH-12)/2
        t=Table([[p("DESIGN A","label"),p("DESIGN B","label")],
                 [image(rel_a,width),image(rel_b,width)]],colWidths=[width+6,width+6])
        t.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),0),
                              ("RIGHTPADDING",(0,0),(-1,-1),6),("TOPPADDING",(0,0),(-1,-1),2),
                              ("BOTTOMPADDING",(0,0),(-1,-1),3)]))
        story.append(t);add(caption,"caption")
    def page():story.append(PageBreak())

    # 1: Outcome and the scope of the numerical study.
    add("AYAZ HUSSAIN  /  ENGINEERING PORTFOLIO  /  NOVEMBER 2026","small")
    add("Diagnostic sample heater","title")
    add("CAD design, transient thermal analysis and heat balance","h2")
    add(f"Reducing the holder height from 20 to 15 mm saves <b>{key['mass_reduction_pct']:.1f}% of the aluminium mass</b>. "
        f"Under the same 10 W input, the minimum well-wall temperature reaches the 60 °C benchmark <b>{key['time_to_60_reduction_pct']:.1f}% sooner</b>. "
        "The thinner holder has a slightly larger wall-temperature range.")
    pair("figures/cad/A_overview.png","figures/cad/B_overview.png",
         "Native CATIA views, cropped only. The complete original screenshots and parameter captures are retained in the evidence folder.")
    table([["Primary result","Design A","Design B"],
           ["Calculated solid mass",f"{g['A']['mass_kg']*1000:.2f} g",f"{g['B']['mass_kg']*1000:.2f} g"],
           ["Minimum wall temperature reaches 60 °C","492.0 s","349.7 s"],
           ["Wall temperature range at that crossing","0.177 °C","0.227 °C"],
           ["Wall temperature range at 600 s","0.183 °C","0.234 °C"],
           ["Whole-body range at 600 s","66.593-66.974 °C","80.617-80.969 °C"]],
           [WIDTH*.48,WIDTH*.26,WIDTH*.26])
    add("The main comparison uses a 1 mm nominal mesh and fixed 1.25 s time step for each design. "
        "Warm-up times are interpolated simulation estimates. The 60 °C value is a comparison benchmark, not a medical assay requirement.","small")
    add("Work completed","h2")
    add("CATIA models of both holders; eight transient thermal cases in Ansys Mechanical; mesh and time-step comparisons; "
        "Python processing of the well-wall histories; warm-up benchmarks and a bulk heat-balance check.")
    add("<b>Scope:</b> temperatures refer to the metal holder with empty wells. Tubes, liquid samples, thermal contact, "
        "a temperature controller and physical prototype tests are not included.")
    page()

    # 2: Model definition.
    title(2,"Geometry and thermal model")
    fig("figures/generated/geometry_parameters.png",
        "Figure 1. Parameter schematic generated from the CAD dimensions; section through one row of blind wells. The coloured base line identifies the heater side.")
    table([["Parameter","Design A","Design B"],
           ["Footprint","60 × 40 mm","60 × 40 mm"],["Overall height","20 mm","15 mm"],
           ["Well diameter / depth / count","8 mm / 12 mm / 6","8 mm / 12 mm / 6"],
           ["Solid floor beneath the wells","8 mm","3 mm"],
           ["Solid volume",f"{g['A']['volume_mm3']:.3f} mm³",f"{g['B']['volume_mm3']:.3f} mm³"],
           ["Convecting area",f"{g['A']['convection_area_m2']*1e6:.3f} mm²",f"{g['B']['convection_area_m2']*1e6:.3f} mm²"]],
          [WIDTH*.44,WIDTH*.28,WIDTH*.28])
    add("Well centres are at 15, 30 and 45 mm along the length and 12 and 28 mm across the width. "
        "The CAD feature sequence is a pad, one blind circular pocket and a rectangular pattern.")
    add("Material","h2")
    add("The ANSYS built-in Aluminum Alloy is used: density 2770 kg/m³ and specific heat 875 J/(kg·K). "
        "Thermal conductivity is temperature dependent: 114, 144, 165 and 175 W/(m·K) at -100, 0, 100 and 200 °C respectively. "
        "No specific commercial alloy grade is inferred from this generic material.")
    add("Load case","h2")
    for text in ["Initial and ambient temperature: 22 °C.",
                 "Heater: constant 10 W on the full 2400 mm² base opposite the well openings.",
                 "Convection: prescribed h = 10 W/(m²·K) on every other surface, including the blind-well walls and floors.",
                 "Transient duration: 600 s; fixed time stepping; results stored at all solved time points."]:
        add("• "+text)
    add("The same power and convection coefficient are used for both designs. The total convecting area changes with height; "
        "a uniform h on cavity and external surfaces is a modelling assumption, not a solved air-flow field.","small")
    page()

    # 3: Warm-up and the distinction between body and wall temperature.
    title(3,"Warm-up response")
    add("The crossing criterion is the first time the <b>minimum exported temperature on the selected cylindrical well walls</b> reaches a benchmark. "
        "All six wells and their axial wall variation are included. Flat well floors are excluded from this particular scope.")
    fig("figures/generated/well_wall_warmup.png",
        "Figure 2. Fine-case histories. Shading spans wall minimum to maximum. The zero-time point is the prescribed 22 °C initial condition.")
    data=[["Minimum wall benchmark","A (s)","B (s)","Time reduction"]]
    for target in [40,50,60,65]:
        aa=next(x for x in m["benchmarks"] if x["design"]=="A" and x["benchmark_C"]==target)
        bb=next(x for x in m["benchmarks"] if x["design"]=="B" and x["benchmark_C"]==target)
        data.append([f"{target} °C",f"{aa['time_s']:.1f}",f"{bb['time_s']:.1f}",f"{100*(1-bb['time_s']/aa['time_s']):.1f}%"])
    table(data,[WIDTH*.40,WIDTH*.18,WIDTH*.18,WIDTH*.24])
    add("At 60 °C, B saves 142.2 s of simulated start-up. Input energy to that point is 4.920 kJ for A and 3.497 kJ for B, "
        "calculated as 10 W × crossing time. These are input energies, not sample energies or measured efficiencies.")
    pair("figures/ansys/A_temperature_well_side.png","figures/ansys/B_temperature_well_side.png",
         "Figure 3. Whole-body ANSYS temperature fields at 600 s. Original colour scales are independently set; compare the numerical legends, not colours alone.")
    add("At 600 s, B is hotter because this is a constant-power warm-up test. The model does not regulate or hold a target temperature.","small")
    page()

    # 4: Spatial trade-off.
    title(4,"Well-wall temperature uniformity")
    fig("figures/generated/well_wall_uniformity.png",
        "Figure 4. Wall range over time and at matched minimum wall temperature. Range = maximum minus minimum across the selected cylindrical walls.")
    table([["Metric","A","B"],
           ["Range when minimum wall reaches 60 °C","0.177 °C","0.227 °C"],
           ["Wall minimum at 600 s","66.621 °C","80.654 °C"],
           ["Wall maximum at 600 s","66.804 °C","80.888 °C"],
           ["Wall range at 600 s","0.183 °C","0.234 °C"],
           ["Whole-body range at 600 s","0.381 °C","0.352 °C"]],
           [WIDTH*.52,WIDTH*.24,WIDTH*.24])
    pair("figures/ansys/A_wellwalls.png","figures/ansys/B_wellwalls.png",
         "Figure 5. ANSYS result scoped to 12 cylindrical face patches representing six well walls. The independently scaled legends and all numerical values are retained.")
    add("B increases the wall range by about 0.050 °C at the 60 °C minimum-wall benchmark. "
        "Although its whole-body range is smaller at 600 s, that does not establish better well-wall uniformity. "
        "The comparison therefore favours B for mass and start-up, while A has the smaller wall range in this model.")
    add("The reported range combines variation within each well and between wells. It is not a range of six per-well mean temperatures. "
        "No experimental uniformity tolerance or fluid-sample temperature claim is inferred.","small")
    page()

    # 5: Derivation and numerical consistency check.
    title(5,"Bulk heat-balance check")
    add("The geometry supplies the thermal capacitance and convecting area. Identical well floors replace equal-area disks removed from the top face, "
        "so the area expression includes the bore walls without double counting the disks.")
    for line in ["V = L W H - n π D² d / 4;  C = ρ V c<sub>p</sub>",
                 "A<sub>conv</sub> = L W + 2 H (L + W) + n π D d",
                 "C dT/dt = P - h A<sub>conv</sub> (T - T<sub>ambient</sub>)",
                 "τ = C / (h A<sub>conv</sub>)",
                 "T(t) = T<sub>ambient</sub> + (T<sub>initial</sub> - T<sub>ambient</sub>) exp(-t/τ) + [P/(h A<sub>conv</sub>)] [1 - exp(-t/τ)]"]:
        add(line,"formula")
    table([["Quantity","A","B"],
           ["Thermal capacitance C",f"{g['A']['capacity_J_K']:.3f} J/K",f"{g['B']['capacity_J_K']:.3f} J/K"],
           ["Thermal conductance hA",f"{g['A']['conductance_W_K']:.6f} W/K",f"{g['B']['conductance_W_K']:.6f} W/K"],
           ["Bulk time constant",f"{g['A']['time_constant_s']:.1f} s",f"{g['B']['time_constant_s']:.1f} s"],
           ["Initial Biot estimate, Lc = V/A",f"{g['A']['Biot_initial']:.6f}",f"{g['B']['Biot_initial']:.6f}"],
           ["Analytical T at 600 s","66.753 °C","80.772 °C"],
           ["FEA whole-body range at 600 s","66.593-66.974 °C","80.617-80.969 °C"]],
           [WIDTH*.46,WIDTH*.27,WIDTH*.27])
    fig("figures/generated/lumped_heat_balance.png",
        "Figure 6. The lumped prediction lies within the spatial FEA range. The one-state model cannot resolve individual well-wall gradients.")
    add("The small Biot estimates support an approximately uniform bulk temperature [3], but the shared power and loss assumptions remain untested. "
        "This is a model-consistency check, not experimental validation. ANSYS-reported averages are retained as reported statistics; "
        "they are not relabelled as volume- or mass-weighted means.","small")
    page()

    # 6: Controlled numerical checks, including the un-converged observable.
    title(6,"Mesh and time-step sensitivity")
    add("Eight solved cases provide three mesh comparisons and three time-step comparisons. Each pair changes one setting. "
        "Checks use common time points across 0-600 s. This staged set is not a single three-grid sequence at one time step.")
    fig("figures/generated/temperature_sensitivity.png",
        "Figure 7. Maximum absolute difference between body-Tmax histories. 1 mK = 0.001 °C; the tested mesh differences are at the exported temperature resolution.")
    data=[["Controlled comparison","Max |ΔTmax|","Max |ΔTmin|"]]
    for x in m["refinement_checks"]:
        data.append([x["label"].replace("→","to"),f"{x['max_abs_Tmax_difference_C']:.3f} °C",f"{x['max_abs_Tmin_difference_C']:.3f} °C"])
    table(data,[WIDTH*.58,WIDTH*.21,WIDTH*.21])
    add("The body-temperature extrema change little over the tested settings. These changes are not formal error bounds, "
        "and the wall-specific result was exported only for the final cases. A separate mesh-convergence bound for wall spread is not established.")
    add("Heat-flux limitation","h2")
    add("The 600 s local peak increases by 16.94% and 15.01% for the two A mesh comparisons, and 12.97% for B. "
        "The early B flux transient also changes by up to 9.59% in the time-step check. "
        "Pointwise flux accuracy is therefore not claimed. These peaks are retained for interpretation and are not converged design limits.")
    add("Total Heat Flux is a local vector magnitude in W/mm², not the applied heater power [1]. "
        "Contour averaging and result recovery affect the displayed field [2]. "
        "A spatial mean of the unsigned magnitude is not an integrated net heat rate.","small")
    page()

    # 7: Boundary-condition uncertainty and the actionable conclusion.
    title(7,"Convection sensitivity and next steps")
    fig("figures/generated/convection_sensitivity.png",
        "Figure 8. A lumped-model sweep of the assumed convection coefficient. These are analytical calculations, not additional ANSYS solves.")
    add("Changing h between 5 and 15 W/(m²·K) shifts the predicted bulk temperature by several degrees. "
        "That effect is much larger than the observed temperature changes from mesh or time-step refinement. "
        "A detailed model or measurements of the heater, cavity losses and contact paths would be needed to reduce this modelling uncertainty.")
    add("Design conclusion","h2")
    add("Under the specified empty-holder, constant-power case, Design B reduces material mass by 27.0% and the time to the 60 °C wall benchmark by 28.9%. "
        "The wall range increases from 0.177 to 0.227 °C at matched minimum temperature. "
        "B favours mass and warm-up time; A has the smaller wall-temperature range under these conditions.")
    add("Further work","h2")
    add("A device-level study would add tube/sample heat capacity and contact resistance, fixture and radiation losses, "
        "a target-temperature controller, wall-specific refinement checks and physical warm-up/holding measurements. "
        "The supplied evidence supports a numerical design study; it does not establish medical-device performance.")
    add("Sources and reproducibility","h2")
    for text,url in [
        ("[1] ANSYS Mechanical 2026 R1: Heat Flux results","https://ansyshelp.ansys.com/public/Views/Secured/corp/v261/en/wb_sim/ds_Heat_Flux_Result.html"),
        ("[2] ANSYS Mechanical 2026 R1: Averaged and Unaveraged Contour Results","https://ansyshelp.ansys.com/public/Views/Secured/corp/v261/en/wb_sim/ds_Unaveraged_Results.html"),
        ("[3] COMSOL 6.3: Thermal Capacitance and Lumped-Model Theory","https://doc.comsol.com/6.3/doc/com.comsol.help.heat/heat_ug_theory.07.039.html")]:
        add(f'<link href="{url}" color="#24618b">{escape(text)}</link>',"small")
    add("Source evidence: 18 original time tables and 45 original CAD/ANSYS images. "
        "All raw bytes are retained in the repository. Cropped images have exact crop boxes and hashes. "
        "Python scripts regenerate the tables and plots; docs/calculation_walkthrough.md explains the calculations.","small")

    out=ROOT/"docs/Heater_Thermal_Design_Report.pdf"
    def decorate(canvas,doc):
        canvas.saveState()
        canvas.setStrokeColor(RULE);canvas.setLineWidth(.5)
        canvas.line(48,40,W-48,40)
        canvas.setFont("Study",7.5);canvas.setFillColor(GREY)
        canvas.drawString(48,27,"Sample heater | CAD and thermal analysis | November 2026")
        canvas.drawRightString(W-48,27,str(doc.page))
        canvas.restoreState()
    doc=SimpleDocTemplate(str(out),pagesize=A4,rightMargin=MARGIN,leftMargin=MARGIN,
        topMargin=48,bottomMargin=52,title="Diagnostic Sample Heater - CAD and Thermal Analysis",author=conf["author"])
    doc.build(story,onFirstPage=decorate,onLaterPages=decorate)
    print(out)


if __name__=="__main__":
    main()
