# scripts/seed_loo_tasks.R
# ========================
# Process Pairwise70 RDA files and seed pi-atlas work queue for LOO experiment.

library(data.table)
library(metafor)
library(jsonlite)

# Paths
PAIRWISE_DIR <- "C:/Users/mahmo/Pairwise70/data"
QUEUE_DB <- "C:/Users/mahmo/pi-atlas/pi-atlas-queue.duckdb"

# We need a way to talk to DuckDB from R or just output a JSON for Python to seed.
# Python seeding is safer given the existing setup.
MANIFEST_PATH <- "C:/Users/mahmo/pi-atlas/loo_manifest.jsonl"

rda_files <- list.files(PAIRWISE_DIR, pattern = "\\.rda$", full.names = TRUE)

cat(sprintf("Processing %d RDA files...\n", length(rda_files)))

# Open manifest for writing
con <- file(MANIFEST_PATH, "w")

total_mas <- 0
total_fits <- 0

for (f in rda_files) {
  load(f)
  ds_name <- gsub("\\.rda$", "", basename(f))
  dt <- as.data.table(get(ds_name))
  
  # Group by Analysis.number (some reviews have multiple MAs)
  # If Analysis.number is missing, use Analysis.name
  group_col <- if ("Analysis.number" %in% names(dt)) "Analysis.number" else "Analysis.name"
  
  analyses <- dt[, .N, by = group_col][N >= 3, get(group_col)]
  
  for (ana_id in analyses) {
    sub_dt <- dt[get(group_col) == ana_id]
    
    # Extract yi, vi
    # Simplified logic: 
    # 1. Binary? (Experimental.cases exists)
    # 2. Continuous? (Experimental.mean exists)
    # 3. GIV? (GIV.Mean exists)
    
    res <- tryCatch({
      if ("Experimental.cases" %in% names(sub_dt) && !all(is.na(sub_dt$Experimental.cases))) {
        # Binary
        escalc(measure="OR", ai=Experimental.cases, n1i=Experimental.N, 
               ci=Control.cases, n2i=Control.N, data=sub_dt)
      } else if ("Experimental.mean" %in% names(sub_dt) && !all(is.na(sub_dt$Experimental.mean))) {
        # Continuous
        escalc(measure="SMD", m1i=Experimental.mean, sd1i=Experimental.SD, n1i=Experimental.N,
               m2i=Control.mean, sd2i=Control.SD, n2i=Control.N, data=sub_dt)
      } else if ("GIV.Mean" %in% names(sub_dt) && !all(is.na(sub_dt$GIV.Mean))) {
        # GIV
        data.frame(yi=sub_dt$GIV.Mean, vi=sub_dt$GIV.SE^2)
      } else {
        NULL
      }
    }, error = function(e) NULL)
    
    if (is.null(res) || any(is.na(res$yi)) || any(is.na(res$vi))) next
    
    total_mas <- total_mas + 1
    k <- nrow(res)
    
    # Create one entry in manifest per MA
    # The Python seeder will expand this into k LOO tasks
    entry <- list(
      ma_id = ds_name,
      analysis_id = as.character(ana_id),
      y = as.numeric(res$yi),
      v = as.numeric(res$vi),
      k = k
    )
    writeLines(toJSON(entry, auto_unbox = TRUE), con)
    total_fits <- total_fits + k
  }
}

close(con)
cat(sprintf("Done. Found %d MAs with k >= 3. Total LOO pairs: %d\n", total_mas, total_fits))
