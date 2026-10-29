    # Check consistency of daily price ranges.
    if (data["High"] < data["Low"]).any():
        raise ValueError(f"{ticker}: High is below Low.")

    # Define the two documented historical OHLC exceptions.
    known_ohlc_exceptions = {
        pd.Timestamp("2015-03-31", tz="UTC"),
        pd.Timestamp("2024-05-01", tz="UTC"),
    }

    # Identify observations where Close falls outside the High-Low range.
    invalid_close = (
        (data["Close"] > data["High"])
        | (data["Close"] < data["Low"])
    )

    # Allow only the two documented exceptions without changing source data.
    exception_rows = data.loc[
        invalid_close & data["date"].isin(known_ohlc_exceptions)
    ]

    for _, row in exception_rows.iterrows():
        logger.warning(
            "%s: preserving known OHLC inconsistency on %s "
            "(Low=%.6f, High=%.6f, Close=%.6f).",
            ticker,
            row["date"].date(),
            row["Low"],
            row["High"],
            row["Close"],
        )

    # Reject all OHLC inconsistencies not explicitly documented.
    unexpected_invalid = invalid_close & ~data["date"].isin(
        known_ohlc_exceptions
    )

    if unexpected_invalid.any():
        invalid_dates = data.loc[unexpected_invalid, "date"].dt.strftime(
            "%Y-%m-%d"
        ).tolist()

        raise ValueError(
            f"{ticker}: Close is outside the High-Low range "
            f"on unexpected dates: {invalid_dates}"
        )