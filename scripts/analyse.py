#!/usr/bin/env python3
"""Reproduce the heater-study tables and figures from the supplied ANSYS exports.

No ANSYS solver is run by this script. Raw exports and original images are read-only.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
COLORS = {"A": "#243e52", "B": "#168273"}


@dataclass
class History:
    time: np.ndarray
    exported_time: np.ndarray
    minimum: np.ndarray
    maximum: np.ndarray
    reported_average: np.ndarray
    source: str

    def temperature_with_initial(self, initial: float):
        return (np.r_[0.0, self.time], np.r_[initial, self.minimum],
                np.r_[initial, self.maximum])


def read_history(path: Path, dt_s: float, end_s: float = 600.0) -> History:
    """Read a time table, validate its scope and recover its fixed solver clock.

    Some GUI exports round a 0.625 s clock to 0.01 s. The original time column
    is retained, while row number * the documented fixed dt supplies the clock
    used for interpolation. An inconsistency greater than 0.0051 s is rejected.
    """
    raw = path.read_bytes()
    text = raw.decode("utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig")
    lines = list(csv.reader(text.splitlines(), delimiter="\t"))
    if not lines or "Time" not in " ".join(lines[0]):
        raise ValueError(f"Expected a time-history table, not a nodal-field file: {path}")
    records = []
    for row in lines[1:]:
        values = [v.strip() for v in row if v.strip()]
        if values:
            if len(values) != 5:
                raise ValueError(f"Unexpected table columns in {path}: {row}")
            records.append([float(v) for v in values])
    a = np.asarray(records, dtype=float)
    n = int(round(end_s / dt_s))
    if a.shape != (n, 5) or not np.isfinite(a).all():
        raise ValueError(f"Missing, extra or nonfinite records in {path}")
    if not np.array_equal(a[:, 0], np.arange(1, n + 1)):
        raise ValueError(f"Broken row sequence in {path}")
    nominal = np.arange(1, n + 1) * dt_s
    if np.max(np.abs(a[:, 1] - nominal)) > 0.0051:
        raise ValueError(f"File does not match its declared time step: {path}")
    if not np.all((a[:, 2] <= a[:, 4] + 1e-9) & (a[:, 4] <= a[:, 3] + 1e-9)):
        raise ValueError(f"Minimum/average/maximum order is inconsistent in {path}")
    return History(nominal, a[:, 1], a[:, 2], a[:, 3], a[:, 4], path.name)


def geometry(config: dict, design: str) -> dict:
    L, W, H = (config["length_mm"], config["width_mm"], config["heights_mm"][design])
    n, D, d = config["well_count"], config["well_diameter_mm"], config["well_depth_mm"]
    volume_mm3 = L * W * H - n * math.pi * D**2 / 4 * d
    # Removed top disks are replaced by equal-area well floors. Add the bore walls.
    area_mm2 = L * W + 2 * H * (L + W) + n * math.pi * D * d
    mass = volume_mm3 * 1e-9 * config["density_kg_m3"]
    capacity = mass * config["cp_J_kgK"]
    area = area_mm2 * 1e-6
    conductance = config["h_W_m2K"] * area
    k_initial = float(np.interp(config["initial_temperature_C"],
                                config["conductivity_temperature_C"],
                                config["conductivity_W_mK"]))
    return dict(design=design, height_mm=H, floor_mm=H-d, volume_mm3=volume_mm3,
                volume_m3=volume_mm3*1e-9, mass_kg=mass, capacity_J_K=capacity,
                convection_area_m2=area, conductance_W_K=conductance,
                time_constant_s=capacity/conductance,
                k_at_initial_W_mK=k_initial,
                Biot_initial=config["h_W_m2K"]*(volume_mm3*1e-9/area)/k_initial)


def lumped_temperature(time_s, capacity_J_K: float, area_m2: float, h_W_m2K: float,
                       power_W: float, initial_C: float, ambient_C: float):
    t = np.asarray(time_s, dtype=float)
    if capacity_J_K <= 0 or area_m2 < 0 or h_W_m2K < 0:
        raise ValueError("Heat capacity must be positive; area and h must be nonnegative")
    ua = h_W_m2K * area_m2
    if ua == 0:
        return initial_C + power_W * t / capacity_J_K
    decay = np.exp(-ua*t/capacity_J_K)
    return ambient_C + (initial_C-ambient_C)*decay + power_W/ua*(-np.expm1(-ua*t/capacity_J_K))


def first_crossing(time_s, temperature_C, target_C: float) -> float | None:
    """Linearly interpolate the first upward crossing, without extrapolation."""
    t, y = np.asarray(time_s), np.asarray(temperature_C)
    hits = np.flatnonzero(y >= target_C)
    if not len(hits):
        return None
    i = int(hits[0])
    if i == 0:
        return float(t[0])
    return float(t[i-1] + (target_C-y[i-1])/(y[i]-y[i-1])*(t[i]-t[i-1]))


def save_csv(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)


def style_axes(ax, xlabel=None, ylabel=None):
    if xlabel: ax.set_xlabel(xlabel)
    if ylabel: ax.set_ylabel(ylabel)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(True, alpha=.22, linewidth=.6)
    ax.set_axisbelow(True)


def save_figure(fig, name):
    dest = ROOT / "figures/generated"
    for ext in ["png", "svg"]:
        fig.savefig(dest / f"{name}.{ext}", dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def make_figures(config, histories, geoms, benchmark_rows, checks):
    plt.rcParams.update({"font.family":"DejaVu Sans", "font.size":10,
                         "axes.titlesize":12, "axes.labelsize":10,
                         "legend.fontsize":9, "svg.fonttype":"none"})
    finals = {d: histories[f"{d}_1mm_1p25s"] for d in ["A", "B"]}
    # The plotted zero-time temperature is the prescribed initial condition.
    fig, ax = plt.subplots(figsize=(9.6, 5.1), layout="constrained")
    for d, bundle in finals.items():
        t, lo, hi = bundle["walls"].temperature_with_initial(config["initial_temperature_C"])
        ax.fill_between(t, lo, hi, color=COLORS[d], alpha=.25)
        ax.plot(t, lo, color=COLORS[d], lw=2, label=f"{d}: minimum well-wall temperature")
        ax.plot(t, hi, color=COLORS[d], lw=.9, alpha=.7)
        b = next(x for x in benchmark_rows if x["design"] == d and x["benchmark_C"] == 60)
        ax.scatter(b["time_s"], 60, c=COLORS[d], s=38, zorder=4)
        ax.annotate(f"{b['time_s']:.1f} s", (b["time_s"], 60), xytext=(8, -24 if d=="B" else 12),
                    textcoords="offset points", color=COLORS[d], fontweight="bold")
    ax.axhline(60, c="#555b65", ls="--", lw=1, label="60 °C comparison benchmark")
    ax.set(xlim=(0,600), ylim=(20,85), title="Warm-up of the six metal well walls")
    style_axes(ax, "Time (s)", "Temperature (°C)"); ax.legend(loc="upper left")
    save_figure(fig,"well_wall_warmup")

    fig, axes = plt.subplots(1,2,figsize=(10.1,4.2),layout="constrained")
    for d,bundle in finals.items():
        w=bundle["walls"]; spread=w.maximum-w.minimum
        axes[0].plot(w.time,spread,color=COLORS[d],lw=1.8,label=f"Design {d}")
        mask=(w.minimum>=30)&(w.minimum<=65)
        axes[1].plot(w.minimum[mask],spread[mask],color=COLORS[d],lw=1.8)
        b=next(x for x in benchmark_rows if x["design"]==d and x["benchmark_C"]==60)
        axes[1].scatter(60,b["wall_spread_C"],c=COLORS[d],s=32)
        axes[1].annotate(f"{b['wall_spread_C']:.3f} °C",(60,b["wall_spread_C"]),
                         xytext=(-65,10 if d=="B" else -20),textcoords="offset points",color=COLORS[d])
    axes[0].set(title="Spread over time",xlim=(0,600),ylim=(0,.28))
    axes[1].set(title="Comparison at matched wall temperature",xlim=(30,65),ylim=(.12,.26))
    axes[1].axvline(60,c="#666",lw=.8,ls="--")
    style_axes(axes[0],"Time (s)","Wall maximum - wall minimum (°C)")
    style_axes(axes[1],"Minimum well-wall temperature (°C)","Wall temperature spread (°C)")
    axes[0].legend(loc="lower right")
    save_figure(fig,"well_wall_uniformity")

    fig,axes=plt.subplots(1,2,figsize=(10.1,4.25),layout="constrained")
    for d,bundle in finals.items():
        h=bundle["temperature"];g=geoms[d]
        t,lo,hi=h.temperature_with_initial(config["initial_temperature_C"])
        model=lumped_temperature(t,g["capacity_J_K"],g["convection_area_m2"],config["h_W_m2K"],
                                 config["heater_power_W"],config["initial_temperature_C"],config["ambient_temperature_C"])
        axes[0].fill_between(t,lo,hi,color=COLORS[d],alpha=.27)
        axes[0].plot(t,model,color=COLORS[d],ls="--",lw=1.7,label=f"{d}: lumped heat balance")
        axes[1].fill_between(t,lo-model,hi-model,color=COLORS[d],alpha=.25,label=f"{d}: FEA min/max band")
    axes[0].set(title="Bulk heating check",xlim=(0,600),ylim=(20,85))
    axes[1].set(title="FEA temperature band relative to lumped model",xlim=(0,600))
    axes[1].axhline(0,c="#555",lw=.8)
    style_axes(axes[0],"Time (s)","Temperature (°C)")
    style_axes(axes[1],"Time (s)","FEA temperature - lumped temperature (°C)")
    axes[0].legend();axes[1].legend()
    save_figure(fig,"lumped_heat_balance")

    fig,axes=plt.subplots(1,2,figsize=(10.1,4.35),layout="constrained")
    for ax,kind,title in zip(axes,["mesh","time"],["Mesh sensitivity","Time-step sensitivity"]):
        records=[x for x in checks if x["kind"]==kind]
        labels=[x["label"] for x in records]; values=[1000*x["max_abs_Tmax_difference_C"] for x in records]
        y=np.arange(len(records))
        ax.barh(y,values,color=[COLORS[x["design"]] for x in records],height=.52)
        ax.set_yticks(y,labels,fontsize=8);ax.invert_yaxis()
        ax.set(title=title,xlim=(0,max(values)*1.38))
        for i,v in enumerate(values):ax.text(v+max(values)*.035,i,f"{v:.0f} mK",va="center",fontsize=9)
        style_axes(ax,"Maximum |difference in body Tmax| (mK)")
    save_figure(fig,"temperature_sensitivity")

    fig,ax=plt.subplots(figsize=(9.6,4.6),layout="constrained")
    hs=np.linspace(5,15,81)
    for d,g in geoms.items():
        vals=[float(lumped_temperature(600,g["capacity_J_K"],g["convection_area_m2"],h,
                  config["heater_power_W"],22,22)) for h in hs]
        ax.plot(hs,vals,color=COLORS[d],lw=2,label=f"Design {d}")
        ax.scatter([10],[vals[40]],c=COLORS[d],s=35)
    ax.axvline(10,c="#555",lw=.8,ls="--",label="FEA assumption: h = 10")
    ax.set(title="Effect of assumed convection on the bulk heat-balance model",xlim=(5,15))
    style_axes(ax,"Uniform convection coefficient h (W/m²K)","Lumped temperature at 600 s (°C)")
    ax.legend(); save_figure(fig,"convection_sensitivity")

    fig,axes=plt.subplots(1,3,figsize=(10.6,3.65),layout="constrained",gridspec_kw={"width_ratios":[1.5,1,1]})
    ax=axes[0]; ax.add_patch(Rectangle((0,0),60,40,facecolor="#edf2f5",edgecolor="#334b60",lw=1.3))
    for x in config["well_centres_x_mm"]:
        for y in config["well_centres_y_mm"]:ax.add_patch(Circle((x,y),4,fill=False,ec="#334b60",lw=1.2))
    ax.set(xlim=(-7,67),ylim=(-8,48),aspect="equal",title="Shared plan: 60 × 40 mm")
    ax.annotate("6 × Ø8 mm",(45,28),xytext=(32,44),arrowprops=dict(arrowstyle="-",color="#555"),fontsize=9)
    ax.annotate("15 mm pitch",(30,12),xytext=(20,-6),arrowprops=dict(arrowstyle="-",color="#555"),fontsize=9)
    ax.axis("off")
    for ax,d in zip(axes[1:],["A","B"]):
        H=config["heights_mm"][d]
        ax.add_patch(Rectangle((0,0),60,H,fc="#d9e3ea",ec=COLORS[d],lw=1.4))
        for x in config["well_centres_x_mm"]:ax.add_patch(Rectangle((x-4,H-12),8,12,fc="white",ec=COLORS[d],lw=1.2))
        ax.plot([0,60],[0,0],lw=3,c="#c35a38")
        ax.set(xlim=(-3,65),ylim=(-9,27),aspect="equal",title=f"{d}: height {H} mm")
        ax.text(30,-4.5,f"Floor {H-12} mm",ha="center",fontsize=9,color=COLORS[d])
        ax.text(30,25,"12 mm-deep blind wells",ha="center",fontsize=8)
        ax.axis("off")
    fig.suptitle("CAD parameter schematic - section through one row of wells",fontsize=12)
    save_figure(fig,"geometry_parameters")


def main():
    config=json.loads((ROOT/"data/cases.json").read_text())
    for p in ["data/processed","results","figures/generated"]:(ROOT/p).mkdir(parents=True,exist_ok=True)
    histories={};audit=[]; summaries=[];geoms={d:geometry(config,d) for d in ["A","B"]}
    for c in config["cases"]:
        h={"temperature":read_history(ROOT/"data/raw"/c["temperature_file"],c["dt_s"]),
           "flux":read_history(ROOT/"data/raw"/c["heatflux_file"],c["dt_s"])}
        if "wellwalls_file" in c:h["walls"]=read_history(ROOT/"data/raw"/c["wellwalls_file"],c["dt_s"])
        histories[c["id"]]=h
        t,q=h["temperature"],h["flux"]
        if np.any(t.minimum<config["initial_temperature_C"]-.001):raise ValueError("Thermal undershoot")
        if np.any(np.diff(t.minimum)<-.002) or np.any(np.diff(t.maximum)<-.002):raise ValueError("Nonmonotonic heating")
        rows=[]
        for i,time in enumerate(t.time):
            row=dict(time_s=float(time),exported_time_s=float(t.exported_time[i]),
                body_min_C=float(t.minimum[i]),body_max_C=float(t.maximum[i]),
                body_reported_average_C=float(t.reported_average[i]),
                heatflux_min_W_mm2=float(q.minimum[i]),heatflux_max_W_mm2=float(q.maximum[i]),
                heatflux_reported_average_W_mm2=float(q.reported_average[i]))
            if "walls" in h:
                w=h["walls"];row.update(wall_min_C=float(w.minimum[i]),wall_max_C=float(w.maximum[i]),
                    wall_reported_average_C=float(w.reported_average[i]),wall_spread_C=float(w.maximum[i]-w.minimum[i]))
            rows.append(row)
        save_csv(ROOT/"data/processed"/f"{c['id']}.csv",rows)
        summaries.append(dict(case=c["id"],design=c["design"],mesh_mm=c["mesh_mm"],dt_s=c["dt_s"],nodes=c["nodes"],elements=c["elements"],
            body_min_C=float(t.minimum[-1]),body_max_C=float(t.maximum[-1]),body_spread_C=float(t.maximum[-1]-t.minimum[-1]),
            body_reported_average_C=float(t.reported_average[-1]),heatflux_max_W_mm2=float(q.maximum[-1]),
            heatflux_max_W_m2=float(q.maximum[-1]*1e6)))
        for kind,obj in h.items():
            p=ROOT/"data/raw"/obj.source
            audit.append(dict(case=c["id"],kind=kind,raw_file=obj.source,rows=len(obj.time),
                dt_s=c["dt_s"],end_s=float(obj.time[-1]),max_export_clock_rounding_s=float(np.max(np.abs(obj.time-obj.exported_time))),
                sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    save_csv(ROOT/"results/case_summary.csv",summaries);save_csv(ROOT/"results/data_audit.csv",audit)
    benchmarks=[]
    for d in ["A","B"]:
        w=histories[f"{d}_1mm_1p25s"]["walls"]
        t,lo,hi=w.temperature_with_initial(config["initial_temperature_C"])
        for target in config["comparison_benchmarks_C"]:
            cross=first_crossing(t,lo,target)
            if cross is None:continue
            high=float(np.interp(cross,t,hi));low=float(np.interp(cross,t,lo))
            benchmarks.append(dict(design=d,benchmark_C=target,time_s=cross,wall_min_C=low,wall_max_C=high,
                wall_spread_C=high-low,input_energy_J=config["heater_power_W"]*cross))
    save_csv(ROOT/"results/benchmark_times.csv",benchmarks)
    pairs=[("mesh","A","A_2mm_5s","A_1p5mm_5s","A: 2 → 1.5 mm; dt 5 s"),
           ("mesh","A","A_1p5mm_2p5s","A_1mm_2p5s","A: 1.5 → 1 mm; dt 2.5 s"),
           ("mesh","B","B_1p5mm_1p25s","B_1mm_1p25s","B: 1.5 → 1 mm; dt 1.25 s"),
           ("time","A","A_1p5mm_5s","A_1p5mm_2p5s","A: 5 → 2.5 s; mesh 1.5 mm"),
           ("time","A","A_1mm_2p5s","A_1mm_1p25s","A: 2.5 → 1.25 s; mesh 1 mm"),
           ("time","B","B_1p5mm_1p25s","B_1p5mm_0p625s","B: 1.25 → 0.625 s; mesh 1.5 mm")]
    checks=[]
    for kind,d,coarse,fine,label in pairs:
        a,b=histories[coarse],histories[fine]
        t=a["temperature"].time
        delta=np.interp(t,b["temperature"].time,b["temperature"].maximum)-a["temperature"].maximum
        dmin=np.interp(t,b["temperature"].time,b["temperature"].minimum)-a["temperature"].minimum
        dq=np.interp(t,b["flux"].time,b["flux"].maximum)-a["flux"].maximum
        checks.append(dict(kind=kind,design=d,coarse_case=coarse,fine_case=fine,label=label,
            max_abs_Tmax_difference_C=float(np.abs(delta).max()),max_abs_Tmin_difference_C=float(np.abs(dmin).max()),
            end_Tmax_difference_C=float(delta[-1]),end_peak_flux_change_pct=float(100*dq[-1]/a["flux"].maximum[-1]),
            max_abs_peak_flux_difference_W_mm2=float(np.abs(dq).max()),
            max_relative_peak_flux_difference_pct=float(np.max(np.abs(dq)/a["flux"].maximum)*100)))
    save_csv(ROOT/"results/refinement_checks.csv",checks)
    bulk=[];sensitivity=[]
    for d,g in geoms.items():
        T=float(lumped_temperature(config["end_time_s"],g["capacity_J_K"],g["convection_area_m2"],
            config["h_W_m2K"],config["heater_power_W"],22,22))
        b=histories[f"{d}_1mm_1p25s"]["temperature"]
        bulk.append(dict(**g,lumped_T600_C=T,FEA_body_min_C=float(b.minimum[-1]),FEA_body_max_C=float(b.maximum[-1]),
            FEA_reported_average_C=float(b.reported_average[-1]),input_energy_J=6000,
            lumped_stored_energy_J=g["capacity_J_K"]*(T-22),lumped_convective_loss_J=6000-g["capacity_J_K"]*(T-22)))
        for h in [5,7.5,10,12.5,15]:
            T=float(lumped_temperature(600,g["capacity_J_K"],g["convection_area_m2"],h,10,22,22))
            sensitivity.append(dict(design=d,h_W_m2K=h,lumped_T600_C=T,model="lumped heat balance; not an additional FEA run"))
    save_csv(ROOT/"results/lumped_check.csv",bulk);save_csv(ROOT/"results/convection_sensitivity.csv",sensitivity)
    a60=next(x for x in benchmarks if x["design"]=="A" and x["benchmark_C"]==60)
    b60=next(x for x in benchmarks if x["design"]=="B" and x["benchmark_C"]==60)
    metrics=dict(geometry=geoms,case_summary=summaries,benchmarks=benchmarks,refinement_checks=checks,lumped_check=bulk,
        key=dict(mass_reduction_pct=100*(1-geoms["B"]["mass_kg"]/geoms["A"]["mass_kg"]),
            time_to_60_reduction_pct=100*(1-b60["time_s"]/a60["time_s"]),
            time_to_60_saved_s=a60["time_s"]-b60["time_s"],
            wall_spread_at_60_A_C=a60["wall_spread_C"],wall_spread_at_60_B_C=b60["wall_spread_C"],
            raw_table_count=len(audit),case_count=len(summaries)))
    (ROOT/"results/metrics.json").write_text(json.dumps(metrics,indent=2)+"\n")
    make_figures(config,histories,geoms,benchmarks,checks)
    print(json.dumps(metrics["key"],indent=2))


if __name__ == "__main__":
    main()
