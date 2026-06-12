# Elysium Wealth Management: Utah crash-data EDA starter
#
# Run `python ingest.py` before using this script. The Python ingestion pipeline
# downloads official UDOT, NHTSA, and Census data and creates the clean files below.

library(tidyverse)
library(scales)

data_dir <- file.path("data", "exports")

# Full anonymized UDOT crash-level data. read_csv() reads the gzip file directly.
utah_crashes <- read_csv(
  file.path(data_dir, "utah_crashes_2019_2024.csv.gz"),
  show_col_types = FALSE
)

# Recommended starting table: one row per Utah county and year.
utah_counties <- read_csv(
  file.path(data_dir, "utah_county_crash_analytics_2019_2024.csv"),
  show_col_types = FALSE
)

# Supporting nationwide datasets.
fars_crashes <- read_csv(
  file.path(data_dir, "fars_crashes_2019_2023.csv"),
  show_col_types = FALSE
)
target_industries <- read_csv(
  file.path(data_dir, "county_target_industries_2023.csv"),
  show_col_types = FALSE
)
county_population <- read_csv(
  file.path(data_dir, "county_population_2020_2024.csv"),
  show_col_types = FALSE
)

# Confirm the loaded datasets.
glimpse(utah_crashes)
glimpse(utah_counties)

# Statewide annual crash and severity trend.
statewide_trend <- utah_crashes |>
  count(year, crash_severity_desc) |>
  arrange(year, desc(n))

print(statewide_trend, n = Inf)

# Latest-year county marketing context.
latest_year <- max(utah_counties$year, na.rm = TRUE)

latest_counties <- utah_counties |>
  filter(year == latest_year) |>
  select(
    county_geoid,
    county_name,
    population,
    all_crashes,
    all_crashes_per_100k,
    injury_crashes,
    suspected_serious_injury_crashes,
    fatal_crashes,
    motor_carrier_crashes,
    commercial_vehicle_crashes,
    target_establishments,
    target_industry_employees
  ) |>
  arrange(desc(all_crashes))

print(latest_counties, n = Inf)

# Compare crash burden and per-capita crash rate.
latest_counties |>
  filter(population >= 10000) |>
  ggplot(aes(x = reorder(county_name, all_crashes_per_100k), y = all_crashes_per_100k)) +
  geom_col(fill = "#31D5D0") +
  coord_flip() +
  labs(
    title = paste(latest_year, "Utah Reported Crashes per 100,000 Residents"),
    subtitle = "Population threshold: 10,000 residents",
    x = NULL,
    y = "Reported crashes per 100,000"
  ) +
  theme_minimal()

# First-pass marketing opportunity scatterplot.
latest_counties |>
  filter(population >= 10000) |>
  ggplot(aes(x = target_industry_employees, y = injury_crashes)) +
  geom_point(
    aes(size = motor_carrier_crashes, color = all_crashes_per_100k),
    alpha = 0.75
  ) +
  geom_text(
    aes(label = county_name),
    check_overlap = TRUE,
    nudge_y = 10,
    size = 3
  ) +
  scale_x_continuous(labels = comma) +
  scale_color_gradient(low = "#31D5D0", high = "#213F57") +
  labs(
    title = "Utah County Market Size and Crash Exposure",
    x = "Employees in target industries",
    y = "Injury crashes",
    size = "Motor-carrier crashes",
    color = "Crashes per 100K"
  ) +
  theme_minimal()

# Street-level crash summary.
street_summary <- utah_crashes |>
  filter(!is.na(main_road_name), main_road_name != "") |>
  group_by(county_name, main_road_name) |>
  summarise(
    all_crashes = n(),
    injury_crashes = sum(crash_severity_desc != "No Injury/PDO", na.rm = TRUE),
    serious_injury_crashes = sum(crash_severity_desc == "Suspected Serious Injury", na.rm = TRUE),
    fatal_crashes = sum(crash_severity_desc == "Fatal", na.rm = TRUE),
    motor_carrier_crashes = sum(motor_carrier_involved_yn == "Y", na.rm = TRUE),
    .groups = "drop"
  ) |>
  arrange(desc(all_crashes))

print(street_summary, n = 30)

