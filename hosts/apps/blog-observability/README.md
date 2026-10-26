# Shared analytics and dashboards

CT112 runs Umami, its private PostgreSQL database and Grafana. Canonical data is
`/srv/appdata/docker/blog-observability`; exact migrated image digests are pinned
in [Compose](compose.yaml), and all three containers remain manually updated.
Existing private URLs and credentials are preserved. No shared media is mounted.

The [observability runbook](../../staging/blog-observability/README.md) owns
installation, migration, verification, backup and rollback. Its blog dashboard
assets stay alongside the CT114 collector configuration, while the applications
and their durable state live here. Use [deploy.sh](deploy.sh) for this host;
CT114's deployment starts only Alloy and Blackbox Exporter.

## Note readership

In Umami, select **The Night Archive — staging**, then Events → Properties.
`map-note-visible` counts a readable note intersecting the actual browser/map
viewport; overview cards and the renderer's offscreen preload margin do not count.
Multiple cards for the same note count once. `map-note-focus`, `map-note-activate`
and `map-note-open` distinguish picker selection, double-click activation and
opening a standalone note. Properties contain the collection and website note URL,
never raw vault paths, note bodies, credentials or persistent reader identifiers.

`map-note-time` records incremental visible/active milliseconds every 15 seconds
and when leaving a note. Active time pauses after 30 seconds without input;
both timers pause when the document is hidden. `map-note-session` records a
completed visible episode. Visibility is sampled once per second; brief exposure
may be missed, and overlapping readable notes can accrue simultaneous time.
These are attention estimates, not proof of reading. DNT and blocked tracking
still apply. Closing/crashing a browser can lose its last interval or completed
episode; historical time cannot be reconstructed.

Run on the operator Mac for combined counts, totals, and mean/median completed
visible episodes (seconds), grouped by readable note URL:

```sh
python3 hosts/apps/blog-observability/note-readership.py --days 7
```

The report uses a read-only SQL transaction through PVE/CT112 and emits CSV.
`--sql` prints the aggregate query; `--website UUID` selects another explicitly
configured website. Umami's Properties UI exposes raw event breakdowns; the
report computes the combined statistics. Existing Grafana operational panels
remain availability/request metrics, not these readership aggregates.
