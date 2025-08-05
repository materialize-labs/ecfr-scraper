"""
eCFR Scraper - Command Line Interface
Main entry point for the Electronic Code of Federal Regulations scraper
"""

import click
import sys
from pathlib import Path
from typing import List, Optional
import json

from src.logger import setup_logging, get_logger
from src.database import ECFRDatabase, DatabaseError
from src.scraper import ECFRScraper, ScrapingError
from config.settings import CFR_TITLES, DB_PATH

logger = get_logger(__name__)


@click.group()
@click.option('--debug', is_flag=True, help='Enable debug logging')
@click.option('--log-file/--no-log-file', default=True, help='Enable/disable file logging')
@click.pass_context
def cli(ctx, debug, log_file):
    """eCFR Scraper - Electronic Code of Federal Regulations data scraper"""
    # Setup logging
    log_level = 'DEBUG' if debug else 'INFO'
    setup_logging(log_level, log_file)
    
    # Store context
    ctx.ensure_object(dict)
    ctx.obj['debug'] = debug
    ctx.obj['log_file'] = log_file


@cli.command()
@click.option('--force', is_flag=True, help='Force re-creation of database schema')
def init_db(force):
    """Initialize the database schema"""
    try:
        logger.info("Initializing database...")
        
        if DB_PATH.exists() and not force:
            if not click.confirm(f"Database already exists at {DB_PATH}. Overwrite?"):
                logger.info("Database initialization cancelled")
                return
        
        with ECFRDatabase() as db:
            db.initialize_schema()
        
        logger.info(f"Database initialized successfully at {DB_PATH}")
        
    except DatabaseError as e:
        logger.error(f"Database initialization failed: {e}")
        sys.exit(1)


@cli.command()
@click.option('--titles', help='Comma-separated list of CFR titles to scrape (1-50)')
@click.option('--force', is_flag=True, help='Force re-download and re-processing of files')
@click.option('--incremental', is_flag=True, help='Only process titles that have been updated')
def scrape(titles, force, incremental):
    """Scrape eCFR data and store in database"""
    try:
        # Parse title numbers
        title_numbers = None
        if titles:
            try:
                title_numbers = [int(x.strip()) for x in titles.split(',')]
                # Validate title numbers
                invalid_titles = [t for t in title_numbers if t not in CFR_TITLES]
                if invalid_titles:
                    raise ValueError(f"Invalid CFR titles: {invalid_titles}")
            except ValueError as e:
                logger.error(f"Invalid titles parameter: {e}")
                sys.exit(1)
        
        # Initialize database connection
        with ECFRDatabase() as db:
            # Check if database is initialized
            try:
                stats = db.get_database_stats()
            except DatabaseError:
                logger.error("Database not initialized. Run 'init-db' first.")
                sys.exit(1)
            
            # Initialize scraper
            scraper = ECFRScraper(db)
            
            try:
                if incremental:
                    logger.info("Starting incremental update...")
                    results = scraper.incremental_update()
                else:
                    logger.info("Starting full scrape...")
                    results = scraper.scrape_all_titles(title_numbers, force)
                
                # Print results
                if results:
                    total_records = sum(results.values())
                    successful_titles = sum(1 for count in results.values() if count > 0)
                    failed_titles = [t for t, count in results.items() if count == 0]
                    
                    click.echo(f"\nScraping Results:")
                    click.echo(f"  Successful titles: {successful_titles}/{len(results)}")
                    click.echo(f"  Total records processed: {total_records}")
                    
                    if failed_titles:
                        click.echo(f"  Failed titles: {failed_titles}")
                    
                    # Show detailed results if debug mode
                    if logger.isEnabledFor(10):  # DEBUG level
                        click.echo(f"\nDetailed Results:")
                        for title_num, record_count in sorted(results.items()):
                            status = "✓" if record_count > 0 else "✗"
                            click.echo(f"  Title {title_num:2d}: {status} {record_count:6d} records")
                else:
                    click.echo("No titles were processed.")
                    
            finally:
                scraper.close()
        
        logger.info("Scraping completed successfully")
        
    except (ScrapingError, DatabaseError) as e:
        logger.error(f"Scraping failed: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
        sys.exit(1)


@cli.command()
@click.option('--titles', help='Comma-separated list of CFR titles to check (1-50)')
def check_updates(titles):
    """Check which titles have been updated since last scrape"""
    try:
        # Parse title numbers
        title_numbers = CFR_TITLES
        if titles:
            try:
                title_numbers = [int(x.strip()) for x in titles.split(',')]
                invalid_titles = [t for t in title_numbers if t not in CFR_TITLES]
                if invalid_titles:
                    raise ValueError(f"Invalid CFR titles: {invalid_titles}")
            except ValueError as e:
                logger.error(f"Invalid titles parameter: {e}")
                sys.exit(1)
        
        with ECFRDatabase() as db:
            scraper = ECFRScraper(db)
            
            try:
                updated_titles = []
                click.echo("Checking for updates...")
                
                for title_number in title_numbers:
                    if scraper.check_for_updates(title_number):
                        updated_titles.append(title_number)
                        click.echo(f"Title {title_number}: Updated")
                    else:
                        click.echo(f"Title {title_number}: Current")
                
                if updated_titles:
                    click.echo(f"\nTitles needing update: {updated_titles}")
                else:
                    click.echo("\nAll titles are up to date.")
                    
            finally:
                scraper.close()
                
    except (ScrapingError, DatabaseError) as e:
        logger.error(f"Update check failed: {e}")
        sys.exit(1)


@cli.command()
def stats():
    """Show database statistics"""
    try:
        with ECFRDatabase() as db:
            stats = db.get_database_stats()
            
            if not stats:
                click.echo("Database appears to be empty or not initialized.")
                return
            
            click.echo("Database Statistics:")
            click.echo("=" * 20)
            for table, count in stats.items():
                click.echo(f"  {table.capitalize():12}: {count:,}")
            
            # Show scraping metadata
            click.echo("\nScraping Status:")
            click.echo("=" * 16)
            
            cursor = db.connection.cursor()
            cursor.execute("""
                SELECT scraping_status, COUNT(*) as count 
                FROM scraping_metadata 
                GROUP BY scraping_status
            """)
            
            for row in cursor.fetchall():
                click.echo(f"  {row['scraping_status'].capitalize():12}: {row['count']}")
            
            # Show recent scraping activity
            cursor.execute("""
                SELECT title_number, last_scraped, scraping_status, records_processed
                FROM scraping_metadata 
                ORDER BY last_scraped DESC 
                LIMIT 10
            """)
            
            recent_scrapes = cursor.fetchall()
            if recent_scrapes:
                click.echo("\nRecent Scraping Activity:")
                click.echo("=" * 25)
                for row in recent_scrapes:
                    click.echo(f"  Title {row['title_number']:2d}: {row['last_scraped']} "
                              f"({row['scraping_status']}) - {row['records_processed']} records")
                              
    except DatabaseError as e:
        logger.error(f"Stats retrieval failed: {e}")
        sys.exit(1)


@cli.command()
@click.argument('query')
@click.option('--limit', default=10, help='Maximum number of results to return')
@click.option('--format', 'output_format', type=click.Choice(['text', 'json']), 
              default='text', help='Output format')
def search(query, limit, output_format):
    """Search sections content using full-text search"""
    try:
        with ECFRDatabase() as db:
            results = db.search_sections(query, limit)
            
            if not results:
                click.echo("No results found.")
                return
            
            if output_format == 'json':
                # Convert datetime objects to strings for JSON serialization
                for result in results:
                    for key, value in result.items():
                        if hasattr(value, 'isoformat'):
                            result[key] = value.isoformat()
                
                click.echo(json.dumps(results, indent=2))
            else:
                click.echo(f"Found {len(results)} results for '{query}':")
                click.echo("=" * 50)
                
                for i, result in enumerate(results, 1):
                    click.echo(f"\n{i}. {result['title_name']} - {result['part_name']}")
                    click.echo(f"   Section {result['section_number']}: {result['section_heading']}")
                    
                    # Show content preview
                    content = result['section_content'] or ""
                    if len(content) > 200:
                        content = content[:200] + "..."
                    click.echo(f"   {content}")
                    
    except DatabaseError as e:
        logger.error(f"Search failed: {e}")
        sys.exit(1)


@cli.command()
@click.argument('backup_path', type=click.Path())
def backup(backup_path):
    """Create a backup of the database"""
    try:
        backup_file = Path(backup_path)
        
        with ECFRDatabase() as db:
            db.backup_database(backup_file)
        
        click.echo(f"Database backed up to: {backup_file}")
        
    except DatabaseError as e:
        logger.error(f"Backup failed: {e}")
        sys.exit(1)


@cli.command()
def vacuum():
    """Optimize database (VACUUM)"""
    try:
        with ECFRDatabase() as db:
            db.vacuum_database()
        
        click.echo("Database optimized successfully")
        
    except DatabaseError as e:
        logger.error(f"Database optimization failed: {e}")
        sys.exit(1)


@cli.command()
@click.option('--title', type=int, help='Show details for specific CFR title')
def list_titles(title):
    """List all CFR titles in database"""
    try:
        with ECFRDatabase() as db:
            cursor = db.connection.cursor()
            
            if title:
                # Show detailed information for specific title
                cursor.execute("""
                    SELECT t.*, 
                           COUNT(DISTINCT c.id) as chapters,
                           COUNT(DISTINCT sc.id) as subchapters,
                           COUNT(DISTINCT p.id) as parts,
                           COUNT(DISTINCT s.id) as sections
                    FROM titles t
                    LEFT JOIN chapters c ON c.title_id = t.id
                    LEFT JOIN subchapters sc ON sc.chapter_id = c.id
                    LEFT JOIN parts p ON p.chapter_id = c.id
                    LEFT JOIN sections s ON s.part_id = p.id
                    WHERE t.title_number = ?
                    GROUP BY t.id
                """, (title,))
                
                row = cursor.fetchone()
                if not row:
                    click.echo(f"Title {title} not found in database.")
                    return
                
                click.echo(f"CFR Title {row['title_number']}: {row['title_name']}")
                click.echo("=" * 60)
                click.echo(f"  Chapters: {row['chapters']}")
                click.echo(f"  Subchapters: {row['subchapters']}")
                click.echo(f"  Parts: {row['parts']}")
                click.echo(f"  Sections: {row['sections']}")
                click.echo(f"  Last Updated: {row['last_updated']}")
                
            else:
                # List all titles
                cursor.execute("""
                    SELECT t.title_number, t.title_name, 
                           COUNT(DISTINCT s.id) as sections,
                           sm.last_scraped, sm.scraping_status
                    FROM titles t
                    LEFT JOIN chapters c ON c.title_id = t.id
                    LEFT JOIN parts p ON p.chapter_id = c.id
                    LEFT JOIN sections s ON s.part_id = p.id
                    LEFT JOIN scraping_metadata sm ON sm.title_number = t.title_number
                    GROUP BY t.id
                    ORDER BY t.title_number
                """)
                
                click.echo("CFR Titles in Database:")
                click.echo("=" * 60)
                click.echo(f"{'Title':<6} {'Sections':<10} {'Status':<12} {'Name'}")
                click.echo("-" * 60)
                
                for row in cursor.fetchall():
                    status = row['scraping_status'] or 'not_scraped'
                    click.echo(f"{row['title_number']:<6} {row['sections']:<10} "
                              f"{status:<12} {row['title_name']}")
                              
    except DatabaseError as e:
        logger.error(f"List operation failed: {e}")
        sys.exit(1)


def main():
    """Main entry point"""
    try:
        cli()
    except KeyboardInterrupt:
        logger.info("Program interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()