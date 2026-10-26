#!/usr/bin/env python3
"""Read aggregate map-note statistics from Umami; no visitor/session data or credentials."""
import argparse
import subprocess
import uuid

STAGING_SITE = 'a3417da8-b984-49df-9e5b-88ecb9b2f6da'


def query(website, days):
    website = str(uuid.UUID(website))
    if not 1 <= days <= 3650:
        raise ValueError('days must be between 1 and 3650')
    return f"""BEGIN READ ONLY;
WITH events AS (
 SELECT e.event_id, e.event_name,
        max(d.string_value) FILTER (WHERE d.data_key='note') AS note,
        max(d.number_value) FILTER (WHERE d.data_key='visible_ms') AS visible_ms,
        max(d.number_value) FILTER (WHERE d.data_key='active_ms') AS active_ms
 FROM website_event e JOIN event_data d ON d.website_event_id=e.event_id
 WHERE e.website_id='{website}' AND e.created_at >= now() - interval '{days} days'
   AND e.event_name LIKE 'map-note-%'
 GROUP BY e.event_id, e.event_name
)
SELECT note,
 count(*) FILTER (WHERE event_name='map-note-visible') AS visible_episodes,
 count(*) FILTER (WHERE event_name='map-note-focus') AS selections,
 count(*) FILTER (WHERE event_name='map-note-open') AS opens,
 round(coalesce(sum(visible_ms) FILTER (WHERE event_name='map-note-time'),0)/1000,2) AS visible_seconds,
 round(coalesce(sum(active_ms) FILTER (WHERE event_name='map-note-time'),0)/1000,2) AS active_seconds,
 round(avg(visible_ms) FILTER (WHERE event_name='map-note-session')/1000,2) AS mean_completed_seconds,
 round((percentile_cont(0.5) WITHIN GROUP (ORDER BY visible_ms) FILTER (WHERE event_name='map-note-session'))::numeric/1000,2) AS median_completed_seconds,
 count(*) FILTER (WHERE event_name='map-note-session') AS completed_episodes
FROM events WHERE note IS NOT NULL GROUP BY note ORDER BY visible_seconds DESC;
COMMIT;
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--website', default=STAGING_SITE)
    parser.add_argument('--days', type=int, default=7)
    parser.add_argument('--sql', action='store_true', help='Print only the read-only aggregate SQL')
    args = parser.parse_args()
    sql = query(args.website, args.days)
    if args.sql:
        print(sql)
        return
    subprocess.run(['ssh', 'root@192.168.0.250', 'pct', 'exec', '112', '--', 'docker', 'exec', '-i',
                    'blog-umami-db', 'psql', '-X', '-q', '--csv', '-v', 'ON_ERROR_STOP=1', '-U', 'umami', '-d', 'umami'],
                   input=sql, text=True, check=True)


if __name__ == '__main__':
    main()
