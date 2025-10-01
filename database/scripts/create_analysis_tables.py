from __future__ import annotations

import asyncio
from sqlalchemy import text

from database.api.database import get_async_session, get_database_manager


DDL_SCHEMA = text("CREATE SCHEMA IF NOT EXISTS stockai;")

DDL_TABLE = text(
    """
    CREATE TABLE IF NOT EXISTS stockai.analysis_daily (
        id BIGSERIAL PRIMARY KEY,
        symbol TEXT NOT NULL,
        time TIMESTAMPTZ NOT NULL,
        config_version TEXT NOT NULL,
        code_version TEXT NOT NULL,

        final_action TEXT NOT NULL,
        final_strength TEXT NOT NULL,
        final_score NUMERIC(6,2) NOT NULL,

        ichimoku_context TEXT NOT NULL,
        momentum_context TEXT NULL,
        transition_note TEXT NULL,

        rsi NUMERIC(8,4) NULL,
        macd NUMERIC(12,6) NULL,
        macd_signal NUMERIC(12,6) NULL,
        macd_hist NUMERIC(12,6) NULL,
        ma9 NUMERIC(14,4) NULL,
        ma50 NUMERIC(14,4) NULL,
        bb_width NUMERIC(12,6) NULL,
        obv NUMERIC(20,2) NULL,
        tenkan NUMERIC(14,4) NULL,
        kijun NUMERIC(14,4) NULL,
        senkou_a NUMERIC(14,4) NULL,
        senkou_b NUMERIC(14,4) NULL,

        indicators JSONB NOT NULL,
        signals_today JSONB NOT NULL,
        score_details JSONB NOT NULL,
        dataset_meta JSONB NOT NULL,

        prices_source TEXT NOT NULL,
        foreign_source TEXT NULL,
        dataset_hash TEXT NOT NULL,
        dataset_rows INT NOT NULL,
        dataset_start TIMESTAMPTZ NOT NULL,
        dataset_end TIMESTAMPTZ NOT NULL,
        prices_max_updated_at TIMESTAMPTZ NOT NULL,
        foreign_max_updated_at TIMESTAMPTZ NULL,

        -- precise ingestion/analysis timestamps for debugging/overwrites
        analysis_ran_at TIMESTAMPTZ DEFAULT NOW(),

        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW(),

        UNIQUE(symbol, time, config_version)
    );
    """
)

DDL_INDEX1 = text("CREATE INDEX IF NOT EXISTS idx_analysis_symbol_time_desc ON stockai.analysis_daily(symbol, time DESC);")
DDL_INDEX2 = text("CREATE INDEX IF NOT EXISTS idx_analysis_time ON stockai.analysis_daily(time);")
DDL_INDEX3 = text("CREATE INDEX IF NOT EXISTS idx_analysis_action_time ON stockai.analysis_daily(final_action, time DESC);")


async def main() -> None:
    get_database_manager().initialize()
    async with get_async_session() as session:
        await session.execute(DDL_SCHEMA)
        await session.execute(DDL_TABLE)
        await session.execute(DDL_INDEX1)
        await session.execute(DDL_INDEX2)
        await session.execute(DDL_INDEX3)
        await session.commit()
        print("analysis_daily table ready")


if __name__ == "__main__":
    asyncio.run(main())


