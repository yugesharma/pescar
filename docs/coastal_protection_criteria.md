# Spatial Planning & Coastal Sustainability Criteria: Fisheries Tourism (Pescaturismo) in the Azores
**Target Area:** Azores Archipelago, Portugal (European Pilot)  

## Introduction & Contextual Rationale
Transitioning the PescaMare pilot area to the Azores, Portugal, allows us to deploy European Copernicus spatial parameters within a critical regional planning framework. In the Azores, Pescaturismo (Fisheries Tourism) must not operate as an expansion of maritime exploitation. Instead, it must serve as an ecological and socio-economic safeguard. From a physical planning perspective, the goal is to diversify fishermen's income by substituting intensive fishing days with low-impact educational tourism, reducing maritime pressure, and respecting strictly regulated European Marine Protected Areas (MPAs).

---

## Core Spatial Sustainability & Protection Criteria

### 1. Marine Protected Area (MPA) Zoning Safeguards (Source: Copernicus Marine Service & EMODnet)
*   **Copernicus Parameters:** Marine habitat classification, coastal turbidity, and sea surface conditions.
*   **Planning Logic:** The Azores archipelago hosts delicate marine ecosystems (such as hydrothermal vents and seamounts) with strict European ecological constraints. Pescaturismo vessels must visually navigate but never disturb these sanctuaries.
*   **Protection Rule:** The WebGIS enforces **Restricted Tourism Buffers**. The platform overlays official European MPA boundaries, ensuring that tourist-carrying fishing boats are routed only through designated multi-use coastal zones. It sets automated proximity triggers to prevent tourist activity inside strictly protected no-take reserves.

### 2. Fishing Pressure Mitigation and Income Substitution Logic
*   **Copernicus Parameters:** Vessel Density data (derived from Sentinel-1 and AIS tracking) to estimate localized fishing effort.
*   **Planning Logic:** A major ecological risk is "Effort Addition"—where fishermen keep their normal fishing quotas and simply add tourism on top, worsening ecological strain. 
*   **Protection Rule:** The system integrates a **Sustainability Quota Safeguard**. The platform calculates active local fishing pressure hotspots. For a fisherman to register a tourist route on the platform, the planning algorithm requires a verified "Day of Fishing Redirection" (substituting a catch day for a tourism day), directly ensuring a net reduction in regional marine resource extraction.

### 3. Sea State Safety & Low-Impact Coastal Design (Source: Copernicus Marine Service - Wave Models)
*   **Copernicus Parameters:** Significant Wave Height, Wave Period, and Wind-Wave fields.
*   **Planning Logic:** The Azores sea state is volatile and dangerous for small-scale artisanal vessels carrying non-professional tourists. Furthermore, infrastructure supporting tourist boarding must not degrade natural shorelines.
*   **Protection Rule:** The GIS incorporates a dynamic **Maritime Safety & Infrastructure Threshold**. The platform blocks tourism routing in real-time if wave parameters exceed artisanal vessel capacity. For land-side planning, the criteria restrict any new permanent concrete docking infrastructure in rural ports, forcing the use of existing traditional municipal piers to preserve the island's morphology.

---

## System Integration Note for UI/UX (Feedback for Yugesh)
The backend logic must treat tourism as a **conservation lever**. The user interface should visibly track two primary metrics for European evaluators: **"Reduced Fishing Days"** and **"MPA Compliance Score"**. This shifts the application from a commercial booking app to a true spatial decision-support system for sustainable maritime governance.
