# GeoVault Geological QA / Acceptance Guide

Use `GeoVault_Geological_Master_FINAL.xlsx` -> `QA_Test_Cases`.

The 150 test cases are designed to validate:
- attribute lookup
- filtering
- aggregation
- spatial intersection
- buffer/distance queries
- joins between operational and geological data
- provenance/source lookup

A prototype should not answer a spatial question from the LLM alone. Spatial facts should be calculated by the GIS/database layer and then explained by the LLM.
