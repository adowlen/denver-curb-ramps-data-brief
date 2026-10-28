"""Data charts for the Denver curb ramps brief. Brand palette:
dark charcoal background, amber + teal, white text. Every chart labels
its scope and method on the graphic itself. All figures come from
stats.json; no figure from a different scope is juxtaposed without
its label printed on the graphic.
"""
import json, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

root = pathlib.Path(__file__).resolve().parent.parent
s = json.loads((root / "stats.json").read_text())
BG, AMBER, TEAL, FG = "#1c1c1e", "#e8a33d", "#2a9d8f", "#f2f2f2"
plt.rcParams.update({"figure.facecolor": BG, "axes.facecolor": BG,
                     "text.color": FG, "axes.labelcolor": FG,
                     "xtick.color": FG, "ytick.color": FG,
                     "axes.edgecolor": "#555555", "font.size": 10})

# 1. Ramp density by PDI score (area-normalized, zones in the city only)
scores = [str(i) for i in range(1, 11)]
dens = [s["by_score"][k]["ramps_per_sqmi"] for k in scores]
counts = [s["by_score"][k]["ramps"] for k in scores]
bands = [s["by_score"][k]["ranking"] for k in scores]
colors = [{"LOW": "#888888", "MEDIUM": TEAL, "HIGH": AMBER}[b] for b in bands]
fig, ax = plt.subplots(figsize=(8.6, 5.0))
ax.bar(scores, dens, color=colors)
for i, (v, c) in enumerate(zip(dens, counts)):
    ax.text(i, v + 18, f"{v:.0f}\n({c:,})", ha="center", fontsize=8.5)
ax.set_ylim(0, 980)
ax.set_xlabel("PDI score (1 = lowest demand, 10 = highest; LOW 1-4, MEDIUM 5-6, HIGH 7-10)")
ax.set_ylabel("Curb ramps per square mile of zone area")
ax.set_title("Curb ramp density by pedestrian demand score - the peak is in the middle\n"
             f"Scope: {s['placed_ramps']:,} ramps inside Denver's {s['pdi_zones']} PDI zones "
             f"({s['pdi_total_area_sqmi']} sq mi), pulled Oct 28, 2026\n"
             "Bars: ramps per sq mi and (ramps). Score 1 includes two zero-ramp zones covering 34.6 sq mi",
             loc="left", fontsize=10.5)
fig.tight_layout(); fig.savefig(root / "charts" / "chart_density_by_pdi_score.png", dpi=200)
plt.close(fig)

# 2. Pedestrian crashes by demand band: two labeled measures, one scope
cbr = s["crashes_by_ranking"]
order = ["LOW", "MEDIUM", "HIGH"]
fig, axes = plt.subplots(1, 2, figsize=(8.8, 4.8))
ax = axes[0]
vals = [cbr[r]["ped_share_of_crashes_pct"] for r in order]
ns = [cbr[r]["ped_crashes"] for r in order]
tot = [cbr[r]["crashes"] for r in order]
ax.bar(order, vals, color=[ "#888888", TEAL, AMBER])
for i, (v, n, t) in enumerate(zip(vals, ns, tot)):
    ax.text(i, v + 0.12, f"{v}%\n({n:,} of {t:,})", ha="center", fontsize=9)
ax.set_ylim(0, 3.9)
ax.set_ylabel("Pedestrian crashes as % of crashes in band")
ax.set_title("Share of crashes involving a pedestrian", fontsize=10)
ax = axes[1]
vals = [cbr[r]["ped_crashes_per_sqmi_window"] for r in order]
ax.bar(order, vals, color=["#888888", TEAL, AMBER])
for i, (v, n) in enumerate(zip(vals, ns)):
    ax.text(i, v + 1.2, f"{v}\n(n={n:,})", ha="center", fontsize=9)
ax.set_ylim(0, 50)
ax.set_ylabel("Pedestrian crashes per sq mi, 2021-Oct 2026")
ax.set_title("Pedestrian crashes per square mile", fontsize=10)
fig.suptitle("Pedestrian crashes rise with the demand index\n"
             f"Scope: {s['ped_crashes']['in_pdi_zones']:,} pedestrian crashes inside PDI zones, "
             "Denver crash reports 2021 to Oct 15, 2026\n"
             "PDI is a demand proxy from population + employment density, not measured volumes;\n"
             "no exposure-adjusted rate is claimed",
             fontsize=10, x=0.015, ha="left")
fig.tight_layout(rect=[0, 0, 1, 0.84])
fig.savefig(root / "charts" / "chart_ped_crashes_by_band.png", dpi=200)
plt.close(fig)

# 3. Neighborhood ramp density (top 10)
panel = pd.read_csv(root / "data" / "neighborhood_panel.csv")
p = panel.sort_values("ramps_per_sqmi", ascending=False).head(10).iloc[::-1]
fig, ax = plt.subplots(figsize=(8.4, 5.0))
ax.barh(p["neighborhood"], p["ramps_per_sqmi"], color=TEAL)
for i, (v, c) in enumerate(zip(p["ramps_per_sqmi"], p["ramps"])):
    ax.text(v + 25, i, f"{v:,.0f} per sq mi  ({int(c):,} ramps)", va="center", fontsize=9)
ax.set_xlim(0, 1680)
ax.set_xlabel("Curb ramps per square mile (point-in-polygon against the 78 statistical neighborhoods)")
ax.set_title("Where ramps are densest: neighborhoods by ramp density\n"
             f"Scope: {s['neighborhoods']['ramps_placed']:,} ramps inside a neighborhood; "
             "all 78 hold at least one ramp\n"
             f"Median neighborhood density: {s['neighborhoods']['median_density_per_sqmi']} per sq mi. "
             "DIA is lowest at 16.5 (699 ramps, 42.4 sq mi)",
             loc="left", fontsize=10)
fig.tight_layout(); fig.savefig(root / "charts" / "chart_density_by_neighborhood.png", dpi=200)
plt.close(fig)
print("charts done")
