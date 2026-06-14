# Memorandum

**To:** Leadership Team, Elysium Wealth Management  
**From:** McCade Pearson, [mccade.pearson@gmail.com](mailto:mccade.pearson@gmail.com)  
**Date:** June 13, 2026  
**Subject:** Traffic Accident Intelligence Application — Data Sources, Methodology, and Appropriate Use

## Purpose

This memorandum documents the sources, preparation methods, definitions, and known
limitations of the data used in Elysium Wealth Management's Traffic Accident
Intelligence application.

The application was designed to help Elysium evaluate geographic markets by combining
traffic-crash exposure with the size of selected commercial workforces and business
communities. The analysis emphasizes aggregate market conditions and does not identify
or target individual crash victims.

## Executive Summary

- The application's most detailed crash information comes from the
  [Utah Department of Transportation's public Utah Crash Locations service](https://services.arcgis.com/pA2nEVnB6tquxgOW/arcgis/rest/services/Utah_Crash_Locations/FeatureServer).
  This source provides anonymized, street-level records for reported Utah crashes.

- Nationwide fatal-crash comparisons come from the
  [National Highway Traffic Safety Administration's Fatality Analysis Reporting System](https://www.nhtsa.gov/research-data/fatality-analysis-reporting-system-fars).
  NHTSA describes FARS as a nationwide census of fatal injuries suffered in motor
  vehicle traffic crashes.

- County-level commercial-market estimates come from the
  [U.S. Census Bureau's County Business Patterns program](https://www.census.gov/programs-surveys/cbp.html),
  an annual series providing subnational establishment, employment, and payroll data
  by industry.

- Population-adjusted crash rates use official county estimates from the
  [U.S. Census Bureau's Population and Housing Unit Estimates program](https://www.census.gov/programs-surveys/popest.html).

- Data from these sources is downloaded, standardized, joined, and summarized through
  a reproducible Python ingestion pipeline. The Streamlit application uses compact,
  compressed extracts containing only the fields required by the dashboard.

## Primary Data Sources

### 1. Utah Department of Transportation — Utah Crash Locations

- **Official source:** [UDOT Utah Crash Locations Feature Service](https://services.arcgis.com/pA2nEVnB6tquxgOW/arcgis/rest/services/Utah_Crash_Locations/FeatureServer)

- **Application coverage:** Completed calendar years **2019–2024**.

- **Records loaded:** Approximately **354,000 anonymized reported crashes**.

- **Geographic detail:** Individual crash coordinates, county, roadway, route, mileage,
  and location description when reported.

- **Crash characteristics available:**
  - Crash severity
  - Fatality and injury counts
  - Weather and lighting conditions
  - Collision type
  - Number of vehicles involved
  - Work-zone involvement
  - Motor-carrier and commercial-motor-vehicle indicators
  - DUI, distraction, speed, and drowsy-driving indicators
  - Pedestrian, bicyclist, motorcycle, and transit involvement

- **Privacy:** The public service removes personal identification information. The
  application does not contain names, contact details, medical records, or other
  personally identifying victim information.

- **Refresh and recency:** UDOT describes the public service as being refreshed
  regularly, with possible delays for crashes requiring additional investigation.
  Recent-year records may be preliminary or corrected later. For stability, the
  application currently uses completed years through 2024.

- **Important interpretation:** A reported motor-carrier or commercial-vehicle
  indicator is useful evidence of occupational or commercial exposure. It does not
  establish that every person involved in a crash was working at the time.

### 2. National Highway Traffic Safety Administration — FARS

- **Official source:** [NHTSA Fatality Analysis Reporting System](https://www.nhtsa.gov/research-data/fatality-analysis-reporting-system-fars)

- **Application coverage:** Nationwide fatal crashes for **2019–2023**.

- **Purpose in the application:** Provides consistent fatal-crash comparisons across
  states when equivalent all-crash state records are not available.

- **Key fields used:**
  - State and county
  - Crash coordinates
  - Fatality counts
  - Weather and lighting conditions
  - Roadway and work-zone context
  - Large-truck, bus, and recorded motor-carrier indicators

- **Strength:** NHTSA identifies FARS as a nationwide census rather than a statistical
  sample, making it a strong source for fatal-crash analysis.

- **Limitation:** FARS only includes crashes involving a traffic fatality. It should
  not be interpreted as representing all accidents, injuries, or property-damage-only
  events.

### 3. U.S. Census Bureau — County Business Patterns

- **Official source:** [Census County Business Patterns](https://www.census.gov/programs-surveys/cbp.html)

- **Application coverage:** **2023** county-level establishment and employment data.

- **Purpose in the application:** Measures the size of potentially addressable
  commercial markets by county.

- **Selected target industries:**
  - Specialty Trade Contractors
  - Truck Transportation
  - Couriers and Messengers
  - Landscaping Services

- **Measures used:**
  - Number of establishments
  - Number of employees
  - Annual payroll where available

- **Rationale:** These industries represent workers and business owners with meaningful
  driving exposure, including long-distance transportation and local service work.

- **Limitations:**
  - Specialty Trade Contractors includes more occupations than plumbing alone.
  - Census disclosure protections may suppress certain county-industry employment
    values.
  - Industry employment indicates market presence; it does not prove occupational
    involvement in a particular crash.

### 4. U.S. Census Bureau — Population Estimates

- **Official source:** [Census Population and Housing Unit Estimates](https://www.census.gov/programs-surveys/popest.html)

- **Application coverage:** County population estimates for **2020–2024**.

- **Purpose in the application:** Provides denominators for calculating rates such as
  reported crashes or injury crashes per 100,000 residents.

- **Why rates matter:** Raw crash totals naturally favor highly populated counties.
  Per-capita rates provide a second perspective on relative crash exposure.

- **Limitations:**
  - Population-adjusted rates are unavailable for 2019 in the current analytical
    table because the loaded estimate series begins in 2020.
  - Rates in small counties can be volatile. The dashboard applies a population
    threshold when identifying the highest crash-rate county.
  - Resident population does not measure road usage, commuter inflow, tourism, or
    vehicle miles traveled.

## Data Preparation and Analytical Methodology

- Official datasets are downloaded using reproducible scripts rather than manually
  edited spreadsheets.

- Original source fields are standardized into consistent names and data types.

- UDOT county names are matched to Census county identifiers so crash outcomes,
  population estimates, and commercial-market measures can be analyzed together.

- The application maintains a complete Utah county-year analytical table containing
  all **29 Utah counties** for every year from **2019 through 2024**.

- Calculated measures include:
  - All reported crashes per 100,000 residents
  - Injury crashes per 100,000 residents
  - Suspected-serious-injury and fatal-crash counts
  - Motor-carrier and commercial-vehicle crash counts and shares
  - Target-industry establishment and employee totals

- A compact deployment bundle is generated for Streamlit Cloud. The bundle preserves
  the application-required records and fields while reducing deployment data from
  approximately 203 MB to less than 20 MB.

- Local analysis files remain available for more detailed exploratory work in R or
  Python.

## Key Definitions

- **All Reported Crashes:** UDOT crash records across every reported severity,
  including property-damage-only events.

- **Injury Crash:** A UDOT record with a severity other than “No Injury/PDO.”

- **Fatal Crash:** A crash involving at least one traffic fatality.

- **Motor-Carrier-Involved Crash:** A UDOT record indicating motor-carrier
  involvement.

- **Commercial-Vehicle-Involved Crash:** A UDOT record indicating involvement of a
  commercial motor vehicle.

- **Highest Crash Rate:** The county with the highest selected-year crash count per
  100,000 residents, subject to the dashboard's displayed population threshold.

- **Target Businesses and Employees:** Census County Business Patterns totals for the
  four selected industries. These are market-size measures, not crash-involvement
  measures.

## Appropriate Use and Limitations

- Use the application to identify geographic patterns, compare aggregate markets, and
  develop hypotheses for marketing strategy.

- Do not interpret correlation between commercial employment and crash activity as
  proof that employees were working during specific crashes.

- Do not use the application to identify or target individual crash victims.

- Do not treat raw crash totals alone as measures of relative risk. Review population,
  severity, commercial involvement, and market-size measures together.

- Validate major strategic decisions with additional information, including marketing
  costs, Elysium's existing client distribution, competitor presence, referral
  networks, and applicable legal or compliance requirements.

- Recognize that state crash-reporting definitions and completeness can differ.
  Utah's all-crash data is substantially richer than the nationwide FARS-only view.

## Data Refresh Process

- The complete local data pipeline is refreshed by running:

  ```powershell
  python ingest.py
  ```

- The compact Streamlit Cloud deployment bundle is rebuilt by running:

  ```powershell
  python build_deployment_data.py
  ```

- Refresh dates and source record counts are displayed within the application's
  **Data sources and refresh status** section.

## Conclusion

The application combines authoritative government crash, population, and business
datasets into a transparent analytical foundation for market evaluation. The source
data is strong for describing aggregate crash patterns and commercial-market size.
Recommendations concerning where Elysium should market should be treated as strategic
analysis informed by these measures, rather than as conclusions about individual
crash circumstances or occupational involvement.

Please direct questions regarding the application's data methodology or analytical
definitions to: 

**McCade Pearson**  
[mccade.pearson@gmail.com](mailto:mccade.pearson@gmail.com) 

