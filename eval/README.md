# Evaluation Normalization & Matching Rules (`eval/README.md`)

1. **Numeric Matching Tolerance (`M3`, `M5`, `M18`):** Extracted `normalized_value` matches reference `normalized_value` if $|v_{\text{pred}} - v_{\text{ref}}| / \max(|v_{\text{ref}}|, 10^{-9}) \le 0.01$ ($\pm 1\%$) AND `normalized_unit` matches exactly after SI mapping (`Hectares -> ha`, `Tonnes/MT -> tonnes`, `q/ha -> kg/ha` via $\times 100$, `Rs. Lakh -> INR` via $\times 10^5$).
2. **District & Assamese Entity Canonicalization:**
   * `Sibsagar` -> `Sivasagar` (`LGD_AS_300`)
   * `Nowgong` -> `Nagaon` (`LGD_AS_297`)
   * `Borpeta` -> `Barpeta` (`LGD_AS_280`)
   * `কামৰূপ` -> `Kamrup` (`LGD_AS_291`)
   * `যোৰহাট` -> `Jorhat` (`LGD_AS_290`)
3. **Zero Training-Eval Overlap Verification:** All 32 evaluation cases in `eval/cases/` are verified by SHA-256 hash against the adapter fine-tuning split (`0` overlapping hashes).
4. **Judge Calibration (`M6`–`M10`):** Calibrated against 12 human-labeled cases (`100%` agreement $\ge 80\%$ protocol threshold).
