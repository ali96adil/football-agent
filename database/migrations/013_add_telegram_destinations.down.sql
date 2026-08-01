DO $$
BEGIN
    IF EXISTS (
        SELECT telegram_user_id
          FROM core.telegram_identities
         GROUP BY telegram_user_id
        HAVING COUNT(*) > 1
    ) THEN
        RAISE EXCEPTION 'Cannot roll back Telegram composite identities while a sender is linked to multiple chats';
    END IF;
END $$;

DROP TABLE IF EXISTS core.telegram_deliveries;
DROP TABLE IF EXISTS core.telegram_destinations;

ALTER TABLE core.telegram_identities
    DROP CONSTRAINT IF EXISTS telegram_identities_pkey,
    ADD CONSTRAINT telegram_identities_pkey PRIMARY KEY (chat_id),
    ADD CONSTRAINT telegram_identities_telegram_user_id_key UNIQUE (telegram_user_id);
