# octa-stock-report
From your historical daily contract reports from the stock market, generates the P/L statements using FIFO logic.

See fifo_profit.sample.yml.report.csv for an example of the report. View using spreadsheet software for convenience.

Key features:
1. Understands intra-day trading vs delivery.
1. Identifies profit using fifo logic.
1. Report includes daily aggregates.
1. Also includes info about the buys that are being sold.

Missing features:
2. LIFO logic
2. STT tax. The value is accepted, not used.
