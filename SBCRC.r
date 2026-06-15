# Build a 30-team gt table from the Qualtrics rule-changes CSV.
#
# Run with the default CSV location:
#   Rscript 2026_rule_changes_gt_table.R
#
# Or supply a CSV path and optional HTML output path:
#   Rscript 2026_rule_changes_gt_table.R "path/to/responses.csv" "path/to/table.html"

required_packages <- c("dplyr", "gt", "tibble", "tidyr")
missing_packages <- required_packages[
  !vapply(required_packages, requireNamespace, quietly = TRUE, FUN.VALUE = logical(1))
]

if (length(missing_packages) > 0) {
  stop(
    "Install the required packages first: ",
    paste(missing_packages, collapse = ", "),
    call. = FALSE
  )
}

args <- commandArgs(trailingOnly = TRUE)
all_args <- commandArgs(trailingOnly = FALSE)
script_arg <- grep("^--file=", all_args, value = TRUE)
script_dir <- if (length(script_arg) == 1) {
  dirname(normalizePath(sub("^--file=", "", script_arg), winslash = "/"))
} else if (
  requireNamespace("rstudioapi", quietly = TRUE) &&
    rstudioapi::isAvailable() &&
    nzchar(rstudioapi::getActiveDocumentContext()$path)
) {
  dirname(normalizePath(rstudioapi::getActiveDocumentContext()$path, winslash = "/"))
} else {
  getwd()
}

input_path <- if (length(args) >= 1) {
  args[[1]]
} else {
  matching_files <- list.files(
    script_dir,
    pattern = "^2026 Rule Changes.*\\.(csv|xlsx|xls)$",
    full.names = TRUE,
    ignore.case = TRUE
  )

  if (length(matching_files) == 0) {
    stop(
      "No 2026 Rule Changes CSV or Excel file was found beside this script.",
      call. = FALSE
    )
  }

  matching_files[[which.max(file.info(matching_files)$mtime)]]
}

output_path <- if (length(args) >= 2) {
  args[[2]]
} else {
  file.path(script_dir, "2026_rule_changes_gt_table.html")
}

team_lookup <- tibble::tribble(
  ~Team, ~Q1,
  "Albuquerque Armadillos", "CruKEvubububRaSlPLBr",
  "Anaheim Mice", "XEWROnikohlbrUprujIV",
  "Anchorage Killer Whales", "prLbruWrIChaXlmLqeha",
  "Austin Bats", "pajUchopHiSpuMokLYEd",
  "Baltimore Blue Crabs", "muqicuzlstlbrIkEkokU",
  "Birmingham Bandits", "KimlPiFRipLpiCuphETr",
  "Boise Spuds", "sWlchUbUbRlsigudRObR",
  "Buffalo Daredevils", "koplfUglzinoThiwaspi",
  "Cincinnati Chili", "cicIbawijoyOsTecetho",
  "Columbus Arches", "hEylzEcrichupRoJavuP",
  "Des Moines Racoons", "spejuxLRedeYitrlBrlj",
  "El Paso Vipers", "fafrlvUfathuyicichld",
  "Honolulu Diamonds", "tlZlbeRoCrlchosutuWo",
  "Jacksonville Manatees", "phAdrUpUflNUgesOchIF",
  "Kentucky Thoroughbreds", "boPhiCriWAKUfephlJlc",
  "Lansing Lagoon", "CRLSlpRlbrLQlcHlqaho",
  "Lincoln Bully", "SeTriphuKusPlpriJeth",
  "Little Rock Big Foot", "faCHaswocrlsiVlYuplR",
  "Manchester Trout", "hespatRlBEwOrLSwatRa",
  "Nashville Strings", "maqataxlxIclpRujUPHL",
  "Pittsburgh Bridge", "PhOzithIdrUflZuCoprU",
  "Providence Pilgrims", "hOMaSepexeGEniGiswOd",
  "San Diego Seals", "bLmlrLXeThiyaboBLziG",
  "San Jose Seagulls", "yeprIQlcHaxuSWePrIsW",
  "Seattle Brew", "niFasiwewoVowlplkihi",
  "St. Louis 66ers", "DroxUswebudofethOPrl",
  "Tampa Bay Flamingos", "qOtrExicohuBRacoquca",
  "Tulsa Tornado", "cltroxUsToswojikubit",
  "Vancouver Forest", "tuthUsajudrowIbesopr",
  "Vegas Blackjack", "VovEmUmawrlcreMuzEtR"
)

team_lookup$Logo <- c(
  "https://pbs.twimg.com/media/Fxamop_aMAIM8OV?format=png&name=small",
  "https://pbs.twimg.com/media/FxamoqBaQAAQSwY?format=png&name=small",
  "https://pbs.twimg.com/media/FxamoqAaYAEpifP?format=png&name=small",
  "https://pbs.twimg.com/media/FxvLuE8acAAUiBQ?format=png&name=4096x4096",
  "https://pbs.twimg.com/media/Fxamr7daQAAhwSx?format=png&name=4096x4096",
  "https://pbs.twimg.com/media/Fxamr8GaMAE5xbG?format=png&name=small",
  "https://pbs.twimg.com/media/Fxamr80aEAAWgO1?format=png&name=small",
  "https://pbs.twimg.com/media/Fxamr7JaYAADNSj?format=png&name=small",
  "https://pbs.twimg.com/media/FxamtxqaMAAoWvU?format=png&name=small",
  "https://pbs.twimg.com/media/FxamtzbaUAEvyXi?format=png&name=4096x4096",
  "https://pbs.twimg.com/media/FxamtzcaMAAPdlW?format=png&name=small",
  "https://pbs.twimg.com/media/FxamtxraQAANsYd?format=png&name=4096x4096",
  "https://pbs.twimg.com/media/FxamvzcaUAAnl_g?format=png&name=4096x4096",
  "https://pbs.twimg.com/media/FxamvzoaIAAd9nF?format=png&name=4096x4096",
  "https://pbs.twimg.com/media/Fxamv04aQAQl4UB?format=png&name=4096x4096",
  "https://pbs.twimg.com/media/Fxamv1ZacAAfxMM?format=png&name=4096x4096",
  "https://pbs.twimg.com/media/Fxamx14aEAAyD29?format=png&name=4096x4096",
  "https://pbs.twimg.com/media/Fxamx2xaYAAqupS?format=png&name=small",
  "https://pbs.twimg.com/media/Fxamx3nagAAZXCI?format=png&name=4096x4096",
  "https://pbs.twimg.com/media/Fxamx01aMAAD8na?format=png&name=4096x4096",
  "https://pbs.twimg.com/media/Fxam0E7agAAc1zF?format=png&name=small",
  "https://pbs.twimg.com/media/Fxam0GKaQAAlzwx?format=png&name=4096x4096",
  "https://pbs.twimg.com/media/Fxam0INacAIC29O?format=png&name=small",
  "https://pbs.twimg.com/media/Fxam0EvaIAAcI_3?format=png&name=4096x4096",
  "https://pbs.twimg.com/media/Fxam1s5aAAIanao?format=png&name=4096x4096",
  "https://pbs.twimg.com/media/Fxam1ugaEAUkbUi?format=png&name=large",
  "https://pbs.twimg.com/media/FxvLtexaMAA1w50?format=jpg&name=4096x4096",
  "https://pbs.twimg.com/media/Fxam1s7aQAAiSsW?format=png&name=small",
  "https://pbs.twimg.com/media/Fxam4eaaMAAW6Pz?format=png&name=small",
  "https://pbs.twimg.com/media/Fxam4dlaIAIKnBb?format=png&name=4096x4096"
)

question_columns <- paste0("Q", 7:12)

input_extension <- tolower(tools::file_ext(input_path))

if (input_extension == "csv") {
  if (!requireNamespace("readr", quietly = TRUE)) {
    stop("Install the readr package to load CSV files.", call. = FALSE)
  }

  raw_responses <- readr::read_csv(
    input_path,
    show_col_types = FALSE,
    na = c("", "NA")
  )
} else if (input_extension %in% c("xlsx", "xls")) {
  if (!requireNamespace("readxl", quietly = TRUE)) {
    stop("Install the readxl package to load Excel files.", call. = FALSE)
  }

  raw_responses <- readxl::read_excel(input_path, na = c("", "NA"))
} else {
  stop("Input must be a CSV, XLSX, or XLS file.", call. = FALSE)
}

required_columns <- c("RecordedDate", "Q1", question_columns)
missing_columns <- setdiff(required_columns, names(raw_responses))
if (length(missing_columns) > 0) {
  stop(
    "The CSV is missing required columns: ",
    paste(missing_columns, collapse = ", "),
    call. = FALSE
  )
}

question_text <- raw_responses |>
  dplyr::slice(1) |>
  dplyr::select(dplyr::all_of(question_columns)) |>
  unlist(use.names = TRUE) |>
  as.character()

question_labels <- stats::setNames(
  lapply(
    question_text,
    function(question) {
      question <- trimws(question)
      question <- gsub("[\r\n]+", " ", question)
      question <- gsub("\\s+", " ", question)
      gt::html(paste(strwrap(question, width = 42), collapse = "<br>"))
    }
  ),
  question_columns
)

# Parsing RecordedDate removes the two Qualtrics metadata rows automatically.
responses <- raw_responses |>
  dplyr::mutate(
    .source_row = dplyr::row_number(),
    RecordedDate = as.POSIXct(
      RecordedDate,
      format = "%Y-%m-%d %H:%M:%S",
      tz = "America/Denver"
    )
  ) |>
  dplyr::filter(!is.na(RecordedDate), !is.na(Q1))

unknown_ids <- responses |>
  dplyr::anti_join(team_lookup, by = "Q1") |>
  dplyr::distinct(Q1) |>
  dplyr::pull(Q1)

if (length(unknown_ids) > 0) {
  warning(
    "Ignoring unknown Q1 team ID(s): ",
    paste(unknown_ids, collapse = ", "),
    call. = FALSE
  )
}

# Sorting newest-first and then using distinct() retains one latest row per team.
# The source-row tie breaker makes identical timestamps deterministic.
latest_responses <- responses |>
  dplyr::inner_join(team_lookup, by = "Q1") |>
  dplyr::arrange(dplyr::desc(RecordedDate), dplyr::desc(.source_row)) |>
  dplyr::distinct(Team, .keep_all = TRUE)

# Adjust these labels here if the survey's numeric coding is different.
answer_labels <- c("1" = "Yes", "2" = "No")

table_data <- team_lookup |>
  dplyr::select(Team, Logo) |>
  dplyr::left_join(
    latest_responses |>
      dplyr::select(Team, dplyr::all_of(question_columns)),
    by = "Team"
  ) |>
  dplyr::mutate(
    dplyr::across(
      dplyr::all_of(question_columns),
      ~ dplyr::recode(as.character(.x), !!!answer_labels, .default = as.character(.x))
    )
  )

yes_counts <- table_data |>
  dplyr::summarise(
    dplyr::across(dplyr::all_of(question_columns), ~ as.character(sum(.x == "Yes", na.rm = TRUE)))
  ) |>
  dplyr::mutate(Team = "Yes Count", Logo = "", .before = 1)

no_counts <- table_data |>
  dplyr::summarise(
    dplyr::across(dplyr::all_of(question_columns), ~ as.character(sum(.x == "No", na.rm = TRUE)))
  ) |>
  dplyr::mutate(Team = "No Count", Logo = "", .before = 1)

table_data <- table_data |>
  tidyr::replace_na(stats::setNames(as.list(rep("No response", 6)), question_columns))

stopifnot(nrow(table_data) == 30, dplyr::n_distinct(table_data$Team) == 30)

table_data <- dplyr::bind_rows(table_data, yes_counts, no_counts)

rule_changes_gt <- table_data |>
  gt::gt(rowname_col = "Team") |>
  gt::tab_header(
    title = gt::md("**2026 Rule Changes**"),
    subtitle = "Most recent response from each team"
  ) |>
  gt::cols_label(
    Logo = "",
    Q7 = question_labels[["Q7"]],
    Q8 = question_labels[["Q8"]],
    Q9 = question_labels[["Q9"]],
    Q10 = question_labels[["Q10"]],
    Q11 = question_labels[["Q11"]],
    Q12 = question_labels[["Q12"]]
  ) |>
  gt::text_transform(
    fn = function(url) gt::web_image(url = url, height = 35),
    locations = gt::cells_body(columns = Logo)
  ) |>
  gt::cols_width(Logo ~ gt::px(50)) |>
  gt::cols_align(align = "center", columns = dplyr::all_of(question_columns)) |>
  gt::tab_source_note(
    source_note = "Response coding shown as 1 = Yes and 2 = No. The bottom rows count Yes and No answers from each team's latest submission."
  ) |>
  gt::tab_options(
    table.font.names = c("Arial", "sans-serif"),
    table.width = gt::pct(100),
    row.striping.include_table_body = TRUE,
    data_row.padding = gt::px(5)
  )

for (question in question_columns) {
  summary_fill <- if (as.numeric(yes_counts[[question]]) >= 23) {
    "#D9EAD3"
  } else {
    "#F4CCCC"
  }

  summary_text <- if (as.numeric(yes_counts[[question]]) >= 23) {
    "#274E13"
  } else {
    "#990000"
  }

  rule_changes_gt <- rule_changes_gt |>
    gt::tab_style(
      style = list(
        gt::cell_fill(color = summary_fill),
        gt::cell_text(color = summary_text, weight = "bold")
      ),
      locations = gt::cells_body(
        columns = dplyr::all_of(question),
        rows = Team %in% c("Yes Count", "No Count")
      )
    ) |>
    gt::tab_style(
      style = list(
        gt::cell_fill(color = "#D9EAD3"),
        gt::cell_text(color = "#274E13", weight = "bold")
      ),
      locations = gt::cells_body(
        columns = dplyr::all_of(question),
        rows = table_data[[question]] == "Yes"
      )
    ) |>
    gt::tab_style(
      style = list(
        gt::cell_fill(color = "#F4CCCC"),
        gt::cell_text(color = "#990000", weight = "bold")
      ),
      locations = gt::cells_body(
        columns = dplyr::all_of(question),
        rows = table_data[[question]] == "No"
      )
    ) |>
    gt::tab_style(
      style = gt::cell_text(color = "#777777", style = "italic"),
      locations = gt::cells_body(
        columns = dplyr::all_of(question),
        rows = table_data[[question]] == "No response"
      )
    )
}

gt::gtsave(rule_changes_gt, filename = output_path)

message("Saved gt table to: ", normalizePath(output_path, winslash = "/", mustWork = FALSE))
message("Teams with a matched response: ", nrow(latest_responses), " of 30")

if (interactive()) {
  print(rule_changes_gt)
}
