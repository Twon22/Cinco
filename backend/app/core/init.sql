CREATE DATABASE IF NOT EXISTS cinco;
USE cinco;

-- Raw H1 OHLC bars uploaded from MT4 export
CREATE TABLE IF NOT EXISTS daily_bars (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    bar_date    DATE NOT NULL,
    bar_time    TIME NOT NULL,
    open        DECIMAL(10,2) NOT NULL,
    high        DECIMAL(10,2) NOT NULL,
    low         DECIMAL(10,2) NOT NULL,
    close       DECIMAL(10,2) NOT NULL,
    volume      BIGINT,
    UNIQUE KEY uq_bar (bar_date, bar_time)
);

-- Computed Fibonacci levels per trading day
CREATE TABLE IF NOT EXISTS computed_levels (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    trade_date  DATE NOT NULL UNIQUE,
    level_00    DECIMAL(10,2),   -- 0.0 (range start)
    level_1     DECIMAL(10,2),   -- 1   (range end)
    level_5_hi  DECIMAL(10,2),   -- $5x (1-side extension)
    level_x_hi  DECIMAL(10,2),   -- $x  (1-side outer)
    level_5_lo  DECIMAL(10,2),   -- 5x  (0.0-side extension)
    level_x_lo  DECIMAL(10,2),   -- x   (0.0-side outer)
    is_tie      BOOLEAN DEFAULT FALSE,
    is_gap      BOOLEAN DEFAULT FALSE,
    is_nested   BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Mechanical alignment matches flagged by the scanner
CREATE TABLE IF NOT EXISTS alignments (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    today_date      DATE NOT NULL,
    prior_date      DATE NOT NULL,
    today_level     VARCHAR(10) NOT NULL,   -- e.g. 'x_hi', 'x_lo'
    prior_level     VARCHAR(10) NOT NULL,
    today_price     DECIMAL(10,2) NOT NULL,
    prior_price     DECIMAL(10,2) NOT NULL,
    diff            DECIMAL(8,2) NOT NULL,
    match_type      VARCHAR(20) NOT NULL,   -- 'x==x', 'x==boundary'
    is_boundary_day BOOLEAN DEFAULT FALSE,
    status          ENUM('pending','reviewed','removed') DEFAULT 'pending',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_alignment (today_date, prior_date, today_level, prior_level)
);

-- Human-verified real trade entries
CREATE TABLE IF NOT EXISTS verified_trades (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    alignment_id    BIGINT REFERENCES alignments(id),
    trade_date      DATE NOT NULL,
    entry_time      TIME NOT NULL,
    entry_price     DECIMAL(10,2) NOT NULL,
    direction       ENUM('buy','sell') NOT NULL,
    sr_reference    VARCHAR(100),           -- e.g. "Jan 05 0.0 (4420.84)"
    entry_type      ENUM('immediate','watch_forward') NOT NULL,
    pips_3day       DECIMAL(10,2),
    pips_4day       DECIMAL(10,2),
    hold_days       TINYINT,
    notes           TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
