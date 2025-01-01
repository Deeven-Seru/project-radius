# Benchmark Results - Project Radius v1.0.0

## Hardware
- Processor: Apple M-series ARM64, 8-core
- Memory: 16 GB LPDDR5 | OS: macOS 14
- Compiler: gcc 13, -O3 -march=native -ffast-math

## Results

| Metric | Requirement | Result |
|:-------|:-----------|:-------|
| Latency (mean) | < 10.00 ms | **0.044 ms** |
| Latency (max)  | < 10.00 ms | **0.061 ms** |
| R2 Accuracy    | > 95.00 %  | **99.914 %** |
| MSE            | < 0.1      | **0.076** |
| r0 estimated   | N/A | 1.1585e+01 m |
| tau0 estimated | N/A | 0.0100 s |

Latency margin: **227x** over 10 ms requirement.
