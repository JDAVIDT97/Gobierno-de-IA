"""Delete expired metadata only on an explicitly supplied SQLite database."""
import argparse,sqlite3,json
from datetime import datetime,timedelta,timezone
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--database',type=Path,required=True);p.add_argument('--days',type=int,default=30);p.add_argument('--apply',action='store_true');a=p.parse_args()
if a.days < 1:p.error('days must be positive')
if not a.database.is_file():p.error('database must already exist')
cut=(datetime.now(timezone.utc)-timedelta(days=a.days)).isoformat()
with sqlite3.connect(a.database) as db:
 n=db.execute('SELECT COUNT(*) FROM audit_logs WHERE timestamp < ?', (cut,)).fetchone()[0]
 if a.apply:db.execute('DELETE FROM audit_logs WHERE timestamp < ?', (cut,));db.commit()
print(json.dumps({'database':str(a.database.resolve()),'cutoff':cut,'eligible':n,'deleted':n if a.apply else 0,'dry_run':not a.apply}))
