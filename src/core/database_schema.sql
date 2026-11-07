
    PRAGMA foreign_keys=ON;

    CREATE TABLE IF NOT EXISTS task_leases (
        kind TEXT NOT NULL, task_key TEXT NOT NULL, owner TEXT NOT NULL,
        expires REAL NOT NULL, cancel_requested INTEGER NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'running', PRIMARY KEY(kind, task_key)
    );
    CREATE INDEX IF NOT EXISTS idx_task_leases_active ON task_leases(kind,status,expires);

    CREATE TABLE IF NOT EXISTS settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT NOT NULL UNIQUE,
        value TEXT NOT NULL,
        value_type TEXT NOT NULL DEFAULT 'string',
        description TEXT,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS news_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT NOT NULL,
        category TEXT NOT NULL,
        title TEXT NOT NULL,
        summary TEXT,
        url TEXT NOT NULL,
        published_at TEXT NOT NULL,
        fetched_at TEXT NOT NULL,
        keywords TEXT,
        dedup_hash TEXT NOT NULL UNIQUE,
        sentiment REAL
    );

    CREATE TABLE IF NOT EXISTS watchlist_group (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        sort_order INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS watchlist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id INTEGER NOT NULL REFERENCES watchlist_group(id) ON DELETE CASCADE,
        symbol TEXT NOT NULL,
        market TEXT NOT NULL,
        name TEXT NOT NULL,
        sort_order INTEGER NOT NULL DEFAULT 0,
        remark TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE(group_id, symbol)
    );

    CREATE TABLE IF NOT EXISTS resource_pools (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        description TEXT,
        source_type TEXT NOT NULL DEFAULT 'manual',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS resource_pool_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pool_id INTEGER NOT NULL REFERENCES resource_pools(id) ON DELETE CASCADE,
        symbol TEXT NOT NULL,
        market TEXT NOT NULL DEFAULT 'CN',
        name TEXT NOT NULL DEFAULT '',
        weight REAL NOT NULL DEFAULT 1.0,
        tags TEXT,
        remark TEXT,
        source TEXT NOT NULL DEFAULT 'manual',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE(pool_id, symbol)
    );

    CREATE TABLE IF NOT EXISTS security_master (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        market TEXT NOT NULL,
        name TEXT NOT NULL,
        abbr TEXT NOT NULL DEFAULT '',
        pinyin TEXT NOT NULL DEFAULT '',
        aliases TEXT NOT NULL DEFAULT '',
        exchange TEXT NOT NULL DEFAULT '',
        asset_type TEXT NOT NULL DEFAULT 'stock',
        is_active INTEGER NOT NULL DEFAULT 1,
        updated_at TEXT NOT NULL,
        UNIQUE(symbol, market)
    );

    CREATE TABLE IF NOT EXISTS stock_relations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        relation_type TEXT NOT NULL,
        source_code TEXT NOT NULL,
        source_name TEXT,
        target_code TEXT NOT NULL,
        target_name TEXT,
        weight REAL NOT NULL DEFAULT 1.0,
        source_note TEXT,
        valid INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS recommend_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        path TEXT NOT NULL,
        conditions TEXT NOT NULL,
        model_name TEXT,
        status TEXT NOT NULL DEFAULT '完成',
        progress INTEGER NOT NULL DEFAULT 100,
        stage TEXT,
        error_msg TEXT,
        created_at TEXT NOT NULL,
        started_at TEXT,
        finished_at TEXT
    );

    CREATE TABLE IF NOT EXISTS recommend_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id INTEGER NOT NULL REFERENCES recommend_tasks(id) ON DELETE CASCADE,
        rank INTEGER NOT NULL,
        symbol TEXT NOT NULL,
        name TEXT NOT NULL,
        score REAL NOT NULL,
        reason TEXT,
        factors TEXT,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS recommend_templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        plan TEXT NOT NULL,
        path TEXT NOT NULL,
        limit_count INTEGER NOT NULL DEFAULT 10,
        universe_text TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS model_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        report_type TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT '完成',
        content TEXT NOT NULL,
        topic TEXT,
        model_name TEXT NOT NULL,
        generated_at TEXT NOT NULL,
        file_path TEXT
    );

    CREATE TABLE IF NOT EXISTS papers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        authors TEXT,
        abstract TEXT,
        source TEXT,
        url TEXT,
        pdf_path TEXT,
        published_at TEXT,
        is_favorite INTEGER NOT NULL DEFAULT 0,
        favorite_note TEXT,
        fetched_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS strategies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        version TEXT NOT NULL DEFAULT 'v1',
        description TEXT,
        param_schema TEXT,
        file_path TEXT NOT NULL,
        interface_type TEXT NOT NULL DEFAULT '统一接口',
        status TEXT NOT NULL DEFAULT '草稿',
        origin TEXT NOT NULL,
        tags TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE(name, version)
    );

    CREATE TABLE IF NOT EXISTS cli_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cli_type TEXT NOT NULL,
        requirement TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT '成功',
        strategy_id INTEGER REFERENCES strategies(id),
        log_path TEXT,
        artifacts TEXT,
        error_msg TEXT,
        created_at TEXT NOT NULL,
        finished_at TEXT
    );

    CREATE TABLE IF NOT EXISTS backtest_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        strategy_id INTEGER NOT NULL REFERENCES strategies(id),
        engine TEXT NOT NULL DEFAULT 'simple',
        symbols TEXT NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        initial_cash REAL NOT NULL,
        commission_rate REAL NOT NULL DEFAULT 0.0003,
        params TEXT,
        benchmark TEXT,
        status TEXT NOT NULL DEFAULT '完成',
        progress INTEGER NOT NULL DEFAULT 100,
        current_date TEXT,
        error_msg TEXT,
        created_at TEXT NOT NULL,
        started_at TEXT,
        finished_at TEXT
    );

    CREATE TABLE IF NOT EXISTS backtest_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id INTEGER NOT NULL UNIQUE REFERENCES backtest_tasks(id) ON DELETE CASCADE,
        metrics TEXT NOT NULL,
        equity_curve TEXT NOT NULL,
        trades TEXT,
        trades_path TEXT,
        report_path TEXT,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS factor_definitions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        factor_key TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        category TEXT NOT NULL DEFAULT 'style',
        expression_key TEXT NOT NULL,
        description TEXT,
        direction TEXT NOT NULL DEFAULT 'positive',
        horizon_days INTEGER NOT NULL DEFAULT 5,
        rebalance_frequency TEXT NOT NULL DEFAULT 'daily',
        enabled INTEGER NOT NULL DEFAULT 1,
        source TEXT NOT NULL DEFAULT 'config',
        threshold_ic REAL NOT NULL DEFAULT 0.02,
        threshold_coverage REAL NOT NULL DEFAULT 0.7,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS factor_metrics_daily (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        factor_key TEXT NOT NULL REFERENCES factor_definitions(factor_key) ON DELETE CASCADE,
        metric_date TEXT NOT NULL,
        universe TEXT NOT NULL,
        ic REAL,
        rank_ic REAL,
        icir REAL,
        hit_rate REAL,
        long_short_return REAL,
        coverage REAL,
        turnover REAL,
        quantile_monotonicity REAL,
        sample_size INTEGER NOT NULL DEFAULT 0,
        metadata TEXT,
        created_at TEXT NOT NULL,
        UNIQUE(factor_key, metric_date, universe)
    );

    CREATE TABLE IF NOT EXISTS factor_alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        factor_key TEXT NOT NULL REFERENCES factor_definitions(factor_key) ON DELETE CASCADE,
        severity TEXT NOT NULL,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'open',
        triggered_at TEXT NOT NULL,
        resolved_at TEXT
    );

    CREATE TABLE IF NOT EXISTS monitor_universes (
        version TEXT PRIMARY KEY,
        payload TEXT NOT NULL,
        observed_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS monitor_reports (
        cache_key TEXT PRIMARY KEY,
        payload TEXT NOT NULL,
        refreshed_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS qlib_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_type TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        workflow_path TEXT,
        provider_uri TEXT,
        params TEXT,
        metrics TEXT,
        artifacts TEXT,
        error_msg TEXT,
        created_at TEXT NOT NULL,
        started_at TEXT,
        finished_at TEXT
    );

    CREATE TABLE IF NOT EXISTS quant_workflow_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mode TEXT NOT NULL,
        sop_id TEXT NOT NULL,
        title TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'in_progress',
        context TEXT,
        summary TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS quant_workflow_steps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER NOT NULL REFERENCES quant_workflow_runs(id) ON DELETE CASCADE,
        step_order INTEGER NOT NULL,
        stage_key TEXT NOT NULL,
        title TEXT NOT NULL,
        status TEXT NOT NULL,
        evidence TEXT,
        artifacts TEXT,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS quant_workflow_artifacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER NOT NULL REFERENCES quant_workflow_runs(id) ON DELETE CASCADE,
        artifact_type TEXT NOT NULL,
        title TEXT NOT NULL,
        ref_type TEXT,
        ref_id TEXT,
        summary TEXT,
        data TEXT,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS paper_accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        strategy_id INTEGER REFERENCES strategies(id),
        initial_cash REAL NOT NULL,
        current_cash REAL NOT NULL,
        status TEXT NOT NULL DEFAULT '运行中',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS paper_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id INTEGER NOT NULL REFERENCES paper_accounts(id) ON DELETE CASCADE,
        symbol TEXT NOT NULL,
        market TEXT NOT NULL,
        direction TEXT NOT NULL,
        order_type TEXT NOT NULL DEFAULT '限价',
        price REAL,
        quantity INTEGER NOT NULL,
        filled_qty INTEGER NOT NULL DEFAULT 0,
        avg_price REAL,
        status TEXT NOT NULL DEFAULT '待撮合',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS paper_trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id INTEGER NOT NULL REFERENCES paper_accounts(id) ON DELETE CASCADE,
        order_id INTEGER NOT NULL REFERENCES paper_orders(id) ON DELETE CASCADE,
        symbol TEXT NOT NULL,
        direction TEXT NOT NULL,
        price REAL NOT NULL,
        quantity INTEGER NOT NULL,
        fee REAL NOT NULL DEFAULT 0,
        traded_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS paper_positions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id INTEGER NOT NULL REFERENCES paper_accounts(id) ON DELETE CASCADE,
        symbol TEXT NOT NULL,
        name TEXT,
        quantity INTEGER NOT NULL DEFAULT 0,
        available_qty INTEGER NOT NULL DEFAULT 0,
        avg_cost REAL NOT NULL DEFAULT 0.0,
        market_value REAL NOT NULL DEFAULT 0.0,
        updated_at TEXT NOT NULL,
        UNIQUE(account_id, symbol)
    );

    CREATE TABLE IF NOT EXISTS paper_nav_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id INTEGER NOT NULL REFERENCES paper_accounts(id) ON DELETE CASCADE,
        nav_date TEXT NOT NULL,
        total_asset REAL NOT NULL,
        cash REAL NOT NULL,
        market_value REAL NOT NULL,
        net_value REAL NOT NULL,
        daily_return REAL,
        created_at TEXT NOT NULL,
        UNIQUE(account_id, nav_date)
    );

    CREATE TABLE IF NOT EXISTS live_configs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        strategy_id INTEGER NOT NULL REFERENCES strategies(id),
        params TEXT,
        channel TEXT NOT NULL DEFAULT 'paper',
        capital REAL NOT NULL,
        risk_controls TEXT,
        status TEXT NOT NULL DEFAULT '启用',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS live_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        config_id INTEGER NOT NULL REFERENCES live_configs(id),
        status TEXT NOT NULL DEFAULT 'running',
        started_at TEXT NOT NULL,
        stopped_at TEXT,
        heartbeat_at TEXT,
        error_msg TEXT,
        log_path TEXT
    );

    CREATE TABLE IF NOT EXISTS live_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER NOT NULL REFERENCES live_runs(id) ON DELETE CASCADE,
        symbol TEXT NOT NULL,
        direction TEXT NOT NULL,
        price REAL,
        quantity INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT '已报',
        channel_order_id TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS kb_categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        parent_id INTEGER NOT NULL DEFAULT 0,
        sort_order INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS kb_documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        doc_type TEXT NOT NULL,
        category_id INTEGER NOT NULL DEFAULT 0,
        summary TEXT,
        content TEXT,
        file_path TEXT,
        source TEXT,
        tags TEXT,
        status TEXT NOT NULL DEFAULT 'ready',
        imported_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        sag_source_id TEXT NOT NULL DEFAULT '',
        sag_document_id TEXT NOT NULL DEFAULT '',
        sag_sync_status TEXT NOT NULL DEFAULT '',
        sag_content_hash TEXT NOT NULL DEFAULT '',
        sag_endpoint_hash TEXT NOT NULL DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS kb_document_chunks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doc_id INTEGER NOT NULL REFERENCES kb_documents(id) ON DELETE CASCADE,
        chunk_index INTEGER NOT NULL,
        heading TEXT,
        content TEXT NOT NULL,
        char_count INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE(doc_id, chunk_index)
    );

    CREATE TABLE IF NOT EXISTS kb_qa_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL DEFAULT 'default',
        question TEXT NOT NULL,
        answer TEXT NOT NULL,
        cited_docs TEXT,
        model_name TEXT,
        qa_scope TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS kb_qa_sessions (
        session_id TEXT PRIMARY KEY,
        name TEXT NOT NULL DEFAULT '',
        summary TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS ai_workspace_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_name TEXT NOT NULL DEFAULT '',
        title TEXT NOT NULL,
        session_type TEXT NOT NULL DEFAULT 'chat',
        status TEXT NOT NULL DEFAULT 'active',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS ai_workspace_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL REFERENCES ai_workspace_sessions(id) ON DELETE CASCADE,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        metadata TEXT,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS remote_sources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_type TEXT NOT NULL,
        name TEXT NOT NULL UNIQUE,
        conn_config TEXT NOT NULL,
        enabled INTEGER NOT NULL DEFAULT 1,
        status TEXT NOT NULL DEFAULT 'disconnected',
        last_sync_at TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS remote_docs_cache (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_id INTEGER NOT NULL REFERENCES remote_sources(id) ON DELETE CASCADE,
        remote_id TEXT NOT NULL,
        title TEXT NOT NULL,
        summary TEXT,
        content TEXT,
        local_path TEXT,
        fetched_at TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE(source_id, remote_id)
    );

    CREATE TABLE IF NOT EXISTS scheduled_jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        cron_expr TEXT NOT NULL,
        job_type TEXT NOT NULL,
        job_params TEXT,
        enabled INTEGER NOT NULL DEFAULT 1,
        last_run_at TEXT,
        next_run_at TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS job_executions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER NOT NULL REFERENCES scheduled_jobs(id) ON DELETE CASCADE,
        triggered_at TEXT NOT NULL,
        trigger_type TEXT NOT NULL DEFAULT 'manual',
        status TEXT NOT NULL DEFAULT '运行中',
        duration_ms INTEGER,
        result_summary TEXT,
        error_msg TEXT,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS llm_models (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        base_url TEXT NOT NULL,
        api_key TEXT NOT NULL,
        model_name TEXT NOT NULL,
        api_key_env TEXT NOT NULL DEFAULT '',
        temperature REAL NOT NULL DEFAULT 0.2,
        max_tokens INTEGER NOT NULL DEFAULT 1200,
        timeout_seconds REAL NOT NULL DEFAULT 60,
        system_prompt TEXT NOT NULL DEFAULT '',
        purpose TEXT NOT NULL,
        level TEXT NOT NULL DEFAULT 'fast',
        is_default INTEGER NOT NULL DEFAULT 0,
        enabled INTEGER NOT NULL DEFAULT 1,
        call_count INTEGER NOT NULL DEFAULT 0,
        success_count INTEGER NOT NULL DEFAULT 0,
        failure_count INTEGER NOT NULL DEFAULT 0,
        total_duration_ms INTEGER NOT NULL DEFAULT 0,
        last_duration_ms INTEGER,
        last_called_at TEXT,
        last_status TEXT NOT NULL DEFAULT '',
        last_error TEXT NOT NULL DEFAULT '',
        remark TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS mcp_services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        service_type TEXT NOT NULL,
        transport TEXT NOT NULL DEFAULT 'stdio',
        conn_params TEXT NOT NULL,
        enabled INTEGER NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'disconnected',
        remark TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS skills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        description TEXT,
        source TEXT,
        param_schema TEXT,
        params TEXT,
        enabled INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE VIRTUAL TABLE IF NOT EXISTS news_items_fts USING fts5(title, summary);
    CREATE VIRTUAL TABLE IF NOT EXISTS kb_documents_fts USING fts5(title, summary, content);
    CREATE VIRTUAL TABLE IF NOT EXISTS kb_document_chunks_fts USING fts5(title, heading, content);

    CREATE TRIGGER IF NOT EXISTS news_items_ai AFTER INSERT ON news_items BEGIN
        INSERT INTO news_items_fts(rowid, title, summary) VALUES (new.id, new.title, COALESCE(new.summary, ''));
    END;
    CREATE TRIGGER IF NOT EXISTS news_items_ad AFTER DELETE ON news_items BEGIN
        DELETE FROM news_items_fts WHERE rowid = old.id;
    END;
    CREATE TRIGGER IF NOT EXISTS news_items_au AFTER UPDATE ON news_items BEGIN
        DELETE FROM news_items_fts WHERE rowid = old.id;
        INSERT INTO news_items_fts(rowid, title, summary) VALUES (new.id, new.title, COALESCE(new.summary, ''));
    END;

    CREATE TRIGGER IF NOT EXISTS kb_documents_ai AFTER INSERT ON kb_documents BEGIN
        INSERT INTO kb_documents_fts(rowid, title, summary, content)
        VALUES (new.id, new.title, COALESCE(new.summary, ''), COALESCE(new.content, ''));
    END;
    CREATE TRIGGER IF NOT EXISTS kb_documents_ad AFTER DELETE ON kb_documents BEGIN
        DELETE FROM kb_documents_fts WHERE rowid = old.id;
    END;
    CREATE TRIGGER IF NOT EXISTS kb_documents_au AFTER UPDATE ON kb_documents BEGIN
        DELETE FROM kb_documents_fts WHERE rowid = old.id;
        INSERT INTO kb_documents_fts(rowid, title, summary, content)
        VALUES (new.id, new.title, COALESCE(new.summary, ''), COALESCE(new.content, ''));
    END;

    CREATE TRIGGER IF NOT EXISTS kb_document_chunks_ai AFTER INSERT ON kb_document_chunks BEGIN
        INSERT INTO kb_document_chunks_fts(rowid, title, heading, content)
        VALUES (
            new.id,
            COALESCE((SELECT title FROM kb_documents WHERE id = new.doc_id), ''),
            COALESCE(new.heading, ''),
            COALESCE(new.content, '')
        );
    END;
    CREATE TRIGGER IF NOT EXISTS kb_document_chunks_ad AFTER DELETE ON kb_document_chunks BEGIN
        DELETE FROM kb_document_chunks_fts WHERE rowid = old.id;
    END;
    CREATE TRIGGER IF NOT EXISTS kb_document_chunks_au AFTER UPDATE ON kb_document_chunks BEGIN
        DELETE FROM kb_document_chunks_fts WHERE rowid = old.id;
        INSERT INTO kb_document_chunks_fts(rowid, title, heading, content)
        VALUES (
            new.id,
            COALESCE((SELECT title FROM kb_documents WHERE id = new.doc_id), ''),
            COALESCE(new.heading, ''),
            COALESCE(new.content, '')
        );
    END;

    CREATE INDEX IF NOT EXISTS idx_news_category_time ON news_items(category, published_at);
    CREATE INDEX IF NOT EXISTS idx_watchlist_group ON watchlist(group_id, sort_order);
    CREATE INDEX IF NOT EXISTS idx_resource_pool_items_pool ON resource_pool_items(pool_id, symbol);
    CREATE INDEX IF NOT EXISTS idx_resource_pools_updated ON resource_pools(updated_at);
    CREATE INDEX IF NOT EXISTS idx_security_master_symbol ON security_master(symbol, market);
    CREATE INDEX IF NOT EXISTS idx_security_master_market_name ON security_master(market, name);
    CREATE INDEX IF NOT EXISTS idx_stock_rel_source ON stock_relations(source_code, relation_type);
    CREATE INDEX IF NOT EXISTS idx_stock_rel_target ON stock_relations(target_code, relation_type);
    CREATE INDEX IF NOT EXISTS idx_recommend_results ON recommend_results(task_id, rank);
    CREATE INDEX IF NOT EXISTS idx_recommend_templates_updated ON recommend_templates(updated_at);
    CREATE INDEX IF NOT EXISTS idx_backtest_tasks_strategy ON backtest_tasks(strategy_id, created_at);
    CREATE INDEX IF NOT EXISTS idx_factor_metrics_key_date ON factor_metrics_daily(factor_key, metric_date);
    CREATE INDEX IF NOT EXISTS idx_factor_alerts_status ON factor_alerts(status, triggered_at);
    CREATE INDEX IF NOT EXISTS idx_qlib_runs_status ON qlib_runs(status, created_at);
    CREATE INDEX IF NOT EXISTS idx_quant_workflow_runs_mode ON quant_workflow_runs(mode, created_at);
    CREATE INDEX IF NOT EXISTS idx_quant_workflow_steps_run ON quant_workflow_steps(run_id, step_order);
    CREATE INDEX IF NOT EXISTS idx_quant_workflow_artifacts_run ON quant_workflow_artifacts(run_id, artifact_type);
    CREATE INDEX IF NOT EXISTS idx_paper_orders_account ON paper_orders(account_id, created_at);
    CREATE INDEX IF NOT EXISTS idx_paper_trades_account ON paper_trades(account_id, traded_at);
    CREATE INDEX IF NOT EXISTS idx_live_runs_config ON live_runs(config_id, started_at);
    CREATE INDEX IF NOT EXISTS idx_kb_documents_category ON kb_documents(category_id);
    CREATE INDEX IF NOT EXISTS idx_kb_document_chunks_doc ON kb_document_chunks(doc_id, chunk_index);
    CREATE INDEX IF NOT EXISTS idx_kb_qa_sessions_updated ON kb_qa_sessions(updated_at);
    CREATE INDEX IF NOT EXISTS idx_ai_workspace_sessions_updated ON ai_workspace_sessions(updated_at);
    CREATE INDEX IF NOT EXISTS idx_ai_workspace_messages_session ON ai_workspace_messages(session_id, id);
    CREATE INDEX IF NOT EXISTS idx_job_executions_job ON job_executions(job_id, triggered_at);
