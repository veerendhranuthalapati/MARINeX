# Vessel Attribution & Scoring Methodology

This document details the mathematical formulation, physics assumptions, and scoring algorithms employed by the MARINeX Vessel Attribution Engine.

---

## 1. Lagrangian Drift Hindcasting Physics

Surface oil transport is governed by the combined advection of surface ocean currents and wind leeway forcing:

$$\vec{v}_{\text{drift}}(t) = \vec{v}_{\text{current}}(t) + \alpha \cdot \vec{v}_{\text{wind}}(t)$$

Where:
- $\vec{v}_{\text{current}}$ is the surface ocean current vector $(u_c, v_c)$ in meters/second.
- $\vec{v}_{\text{wind}}$ is the 10-meter atmospheric wind vector $(u_w, v_w)$ in meters/second.
- $\alpha$ is the leeway wind drift factor (empirically calibrated to $0.032$, or $3.2\%$).

### Backward Time Integration (Hindcast)
To determine where the slick originated, integration proceeds in reverse time:

$$\vec{x}(t - \Delta t) = \vec{x}(t) - \vec{v}_{\text{drift}}(t) \cdot \Delta t + \vec{\eta}_{\text{diffusion}}$$

Where $\vec{\eta}_{\text{diffusion}}$ models horizontal turbulent eddy diffusivity:

$$\sigma_{\text{diffusion}} = \sqrt{2 \cdot D \cdot \Delta t}, \quad D \approx 10.0 \text{ m}^2/\text{s}$$

The 95% confidence convex hull of the back-propagated ensemble particles defines the **Probable Origin Region** polygon.

---

## 2. Four-Factor Candidate Scoring Formulation

Each candidate vessel identified in the spatial-temporal corridor is evaluated across four independent dimensions:

### Factor 1: Proximity Score ($S_{\text{prox}} \in [0, 100]$)
Measures the minimum distance $d_{\text{min}}$ (in km) between the vessel's AIS breadcrumbs and the estimated origin centroid at the Closest Point of Approach (CPA):

$$S_{\text{prox}} = 100 \cdot \exp\left(-\frac{d_{\text{min}}}{\lambda_{\text{prox}}}\right), \quad \lambda_{\text{prox}} = 4.8 \text{ km}$$

- $d_{\text{min}} = 0 \text{ km} \implies S_{\text{prox}} = 100.0$
- $d_{\text{min}} = 3.3 \text{ km} \implies S_{\text{prox}} \approx 50.0$
- $d_{\text{min}} > 15 \text{ km} \implies S_{\text{prox}} < 5.0$

### Factor 2: Temporal Consistency Score ($S_{\text{temp}} \in [0, 100]$)
Measures the temporal discrepancy $|\Delta t|$ (in minutes) between the vessel's arrival at CPA ($t_{\text{CPA}}$) and the inferred spill release epoch ($t_{\text{origin}}$):

$$S_{\text{temp}} = 100 \cdot \exp\left(-\left(\frac{|\Delta t|}{\sigma_{\text{temp}}}\right)^2\right), \quad \sigma_{\text{temp}} = 75.0 \text{ minutes}$$

- $|\Delta t| \le 10 \text{ min} \implies S_{\text{temp}} \ge 98.0$
- $|\Delta t| = 60 \text{ min} \implies S_{\text{temp}} \approx 53.0$
- $|\Delta t| > 150 \text{ min} \implies S_{\text{temp}} < 2.0$

### Factor 3: Trajectory Intersection Score ($S_{\text{traj}} \in [0, 100]$)
Evaluates whether the vessel's reconstructed trajectory LineString penetrates the 95% probable origin uncertainty polygon:

$$S_{\text{traj}} = \begin{cases} 
92.0 & \text{if trajectory intersects origin polygon} \\
75.0 \cdot \exp\left(-\frac{d_{\text{poly}}}{\lambda_{\text{poly}}}\right) & \text{otherwise} \quad (\lambda_{\text{poly}} = 3.5 \text{ km})
\end{cases}$$

### Factor 4: Behavior & Cargo Risk Score ($S_{\text{behav}} \in [0, 100]$)
Assigns baseline prior risk based on vessel category and operational anomalies:
- **Crude Oil Tanker / Chemical Tanker / VLCC**: Base = 75.0 (carries bulk liquid hydrocarbons).
- **Container / Bulk Carrier / General Cargo**: Base = 40.0 (carries heavy fuel oil bunkers).
- **Tug / Supply Vessel / Fishing**: Base = 20.0.
- **Speed Anomaly**: If speed variance exceeds 4.5 knots along the corridor (indicative of slowing down for pump discharge), $+15.0$ points are added.

---

## 3. Composite Candidate Score & Legal Classification

$$S_{\text{overall}} = w_{\text{prox}} S_{\text{prox}} + w_{\text{temp}} S_{\text{temp}} + w_{\text{traj}} S_{\text{traj}} + w_{\text{behav}} S_{\text{behav}}$$

Default configuration weights:
- $w_{\text{prox}} = 0.35$
- $w_{\text{temp}} = 0.25$
- $w_{\text{traj}} = 0.25$
- $w_{\text{behav}} = 0.15$

| Overall Score | Priority Tier | Recommended PSC Action |
|---|---|---|
| **$\ge 75.0$** | **HIGH (Priority 1)** | Urgent inspection notice to next port of call. Demand Oil Record Book (Part II), bilge discharge monitors, and VDR data. |
| **$50.0 - 74.9$** | **MEDIUM (Priority 2)** | Correlate with historical port clearance records and departure fuel bunker receipts. |
| **$25.0 - 49.9$** | **LOW (Priority 3)** | Low evidence correlation. Maintain passive tracking log. |
| **$< 25.0$** | **EXCLUDED** | Inconsistent with drift hindcast. Exclude from active inquiry. |
