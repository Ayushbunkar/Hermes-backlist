import sys
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("db_fixer")

sys.path.insert(0, 'workspace-bl-orchestrator/skills/pipeline')
try:
    import config
except ImportError as e:
    logger.error(f"Cannot import config: {e}")
    sys.exit(1)

def fix_fks():
    try:
        conn = config.get_db_connection()
        c = conn.cursor()
        
        logger.info("Applying ON DELETE CASCADE to foreign keys...")
        c.execute("ALTER TABLE feedback_events DROP CONSTRAINT IF EXISTS feedback_events_opportunity_id_fkey")
        c.execute("ALTER TABLE feedback_events ADD CONSTRAINT feedback_events_opportunity_id_fkey FOREIGN KEY (opportunity_id) REFERENCES opportunities(id) ON DELETE CASCADE")
        
        c.execute("ALTER TABLE opportunities DROP CONSTRAINT IF EXISTS opportunities_project_id_fkey")
        c.execute("ALTER TABLE opportunities ADD CONSTRAINT opportunities_project_id_fkey FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE")
        
        c.execute("ALTER TABLE leads DROP CONSTRAINT IF EXISTS leads_project_id_fkey")
        c.execute("ALTER TABLE leads ADD CONSTRAINT leads_project_id_fkey FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE")
        
        c.execute("ALTER TABLE project_sitemaps DROP CONSTRAINT IF EXISTS project_sitemaps_project_id_fkey")
        c.execute("ALTER TABLE project_sitemaps ADD CONSTRAINT project_sitemaps_project_id_fkey FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE")
        
        conn.commit()
        conn.close()
        logger.info("Database foreign keys successfully upgraded to ON DELETE CASCADE.")
    except Exception as e:
        logger.error(f"Failed to apply DB fixes: {e}")

if __name__ == "__main__":
    fix_fks()
