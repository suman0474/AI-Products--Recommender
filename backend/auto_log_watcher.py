#!/usr/bin/env python3
"""
Auto Log Watcher - Automatic Terminal Data Storage
===================================================

Automatically captures and stores terminal output data into TL*.md files.
Features:
- Stores each word/line of terminal data
- Auto-rotates to new files when 5000 line limit reached
- Supports concurrent/real-time capture
- Creates TL6.md, TL7.md, etc. automatically as needed

Usage Examples:
    # Wrap and capture a command's output:
    python auto_log_watcher.py --wrap "python main.py"
    
    # Watch an existing log file:
    python auto_log_watcher.py --watch logfile.log
    
    # Capture from stdin:
    python main.py 2>&1 | python auto_log_watcher.py --stdin
"""

import os
import sys
import time
import subprocess
import argparse
import signal
from pathlib import Path
from datetime import datetime
from typing import Optional, List, TextIO
import threading


class TerminalLogStorage:
    """Manages storage of terminal data across multiple TL*.md files."""
    
    MAX_LINES_PER_FILE = 5000
    FILE_PREFIX = "TL"
    FILE_EXTENSION = ".md"
    
    def __init__(self, base_dir: Optional[str] = None):
        """Initialize the log storage manager."""
        # Determine base directory for TL files
        script_dir = Path(__file__).parent.resolve()
        
        if base_dir:
            self.base_dir = Path(base_dir).resolve()
        elif script_dir.name == 'backend':
            # Store in parent directory (project root)
            self.base_dir = script_dir.parent
        else:
            self.base_dir = script_dir
        
        self.current_file_num = 1
        self.current_line_count = 0
        self._lock = threading.Lock()
        
        # Initialize the file system
        self._initialize_storage()
        
        print(f"📁 Log storage directory: {self.base_dir}")
        print(f"📝 Current active file: {self.get_current_file_path().name}")
        print("=" * 60)
    
    def _initialize_storage(self):
        """Find or create the appropriate TL file to start with."""
        # Scan existing TL files to find where to continue
        while True:
            file_path = self.get_current_file_path()
            
            if not file_path.exists():
                self._create_new_file(file_path, self.current_file_num)
                break
            
            # Check if current file is full
            line_count = self._count_lines(file_path)
            
            if line_count >= self.MAX_LINES_PER_FILE:
                # File is full, move to next
                self.current_file_num += 1
            else:
                # File has space, use it
                self.current_line_count = line_count
                break
    
    def get_current_file_path(self) -> Path:
        """Get the path of the current active TL file."""
        return self.base_dir / f"{self.FILE_PREFIX}{self.current_file_num}{self.FILE_EXTENSION}"
    
    def _create_new_file(self, file_path: Path, file_num: int):
        """Create a new TL markdown file with header."""
        header = f"""# Terminal Log {file_num}

> Auto-generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
> Maximum lines: {self.MAX_LINES_PER_FILE}
> Auto-managed by: auto_log_watcher.py

---

"""
        try:
            file_path.write_text(header, encoding='utf-8')
            self.current_line_count = header.count('\n')
            print(f"✨ Created new file: {file_path.name}")
        except Exception as e:
            print(f"❌ Error creating file {file_path}: {e}", file=sys.stderr)
            raise
    
    def _count_lines(self, file_path: Path) -> int:
        """Count the number of lines in a file."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                return sum(1 for _ in f)
        except Exception:
            return 0
    
    def store_line(self, line: str):
        """Store a single line of data, handling file rotation if needed."""
        with self._lock:
            # Check if we need to rotate to a new file
            if self.current_line_count >= self.MAX_LINES_PER_FILE:
                self.current_file_num += 1
                new_file_path = self.get_current_file_path()
                self._create_new_file(new_file_path, self.current_file_num)
            
            # Append the line to current file
            try:
                file_path = self.get_current_file_path()
                with open(file_path, 'a', encoding='utf-8') as f:
                    f.write(line)
                    if not line.endswith('\n'):
                        f.write('\n')
                
                self.current_line_count += 1
            except Exception as e:
                print(f"❌ Error writing to file: {e}", file=sys.stderr)
    
    def store_lines(self, lines: List[str]):
        """Store multiple lines of data efficiently."""
        for line in lines:
            self.store_line(line.rstrip('\n'))
    
    def add_section_header(self, title: str):
        """Add a timestamped section header."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        header = f"\n## [{timestamp}] {title}\n"
        self.store_line(header)


class AutoLogWatcher:
    """Main watcher class that handles different capture modes."""
    
    def __init__(self, storage: TerminalLogStorage):
        self.storage = storage
        self.running = True
        
        # Handle graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        print("\n🛑 Shutdown signal received. Stopping...")
        self.running = False
    
    def wrap_command(self, command: str):
        """
        Run a command and capture its output in real-time.
        Output is both displayed to console and stored in TL files.
        """
        print(f"🚀 Running command: {command}")
        print(f"📝 Output will be captured to TL files")
        print("-" * 60)
        
        self.storage.add_section_header(f"Command: {command}")
        
        try:
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,  # Line buffered
                encoding='utf-8',
                errors='replace'
            )
            
            # Read and store output line by line
            while self.running:
                line = process.stdout.readline()
                
                if not line:
                    if process.poll() is not None:
                        break
                    continue
                
                # Display to console
                print(line, end='')
                sys.stdout.flush()
                
                # Store to file
                self.storage.store_line(line.rstrip('\n'))
            
            # Wait for process to complete
            return_code = process.wait()
            
            print("-" * 60)
            print(f"✅ Command finished with return code: {return_code}")
            self.storage.add_section_header(f"Command completed (exit code: {return_code})")
            
        except Exception as e:
            print(f"❌ Error running command: {e}", file=sys.stderr)
            self.storage.store_line(f"ERROR: {e}")
    
    def watch_file(self, file_path: str, interval: float = 1.0):
        """
        Watch a file for new content and store it.
        Similar to 'tail -f' functionality.
        """
        target_file = Path(file_path)
        
        if not target_file.exists():
            print(f"❌ File not found: {file_path}")
            return
        
        print(f"👀 Watching file: {target_file}")
        print(f"📝 New content will be stored to TL files")
        print(f"⏱️  Check interval: {interval}s")
        print("Press Ctrl+C to stop...")
        print("-" * 60)
        
        self.storage.add_section_header(f"Watching file: {target_file}")
        
        # Track file position
        last_position = target_file.stat().st_size
        
        try:
            while self.running:
                current_size = target_file.stat().st_size
                
                if current_size > last_position:
                    # File has new content
                    with open(target_file, 'r', encoding='utf-8', errors='replace') as f:
                        f.seek(last_position)
                        new_lines = f.readlines()
                        
                        for line in new_lines:
                            print(line, end='')
                            self.storage.store_line(line.rstrip('\n'))
                        
                        last_position = f.tell()
                
                elif current_size < last_position:
                    # File was truncated, start from beginning
                    print("⚠️  File was truncated, restarting from beginning...")
                    last_position = 0
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(f"❌ Error watching file: {e}", file=sys.stderr)
        
        print("\n✅ Stopped watching file")
    
    def capture_stdin(self):
        """Capture data from stdin and store it."""
        print("� Reading from stdin...")
        print("📝 Data will be stored to TL files")
        print("-" * 60)
        
        self.storage.add_section_header("Stdin capture")
        
        try:
            for line in sys.stdin:
                print(line, end='')
                self.storage.store_line(line.rstrip('\n'))
        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(f"❌ Error reading stdin: {e}", file=sys.stderr)
        
        print("\n✅ Stdin capture completed")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Auto Log Watcher - Automatic terminal data storage",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Capture command output:
  python auto_log_watcher.py --wrap "python main.py"
  
  # Watch a log file:
  python auto_log_watcher.py --watch app.log
  
  # Pipe from another command:
  python main.py 2>&1 | python auto_log_watcher.py --stdin
  
  # Custom storage directory:
  python auto_log_watcher.py --wrap "python main.py" --dir /path/to/logs
        """
    )
    
    parser.add_argument(
        '--wrap', '-w',
        type=str,
        help='Command to run and capture output from'
    )
    
    parser.add_argument(
        '--watch', '-f',
        type=str,
        help='File to watch for new content (like tail -f)'
    )
    
    parser.add_argument(
        '--stdin',
        action='store_true',
        help='Capture data from stdin'
    )
    
    parser.add_argument(
        '--dir', '-d',
        type=str,
        help='Directory to store TL files (default: auto-detect)'
    )
    
    parser.add_argument(
        '--interval', '-i',
        type=float,
        default=1.0,
        help='Watch interval in seconds (default: 1.0)'
    )
    
    args = parser.parse_args()
    
    # Initialize storage
    try:
        storage = TerminalLogStorage(base_dir=args.dir)
    except Exception as e:
        print(f"❌ Failed to initialize storage: {e}", file=sys.stderr)
        return 1
    
    # Initialize watcher
    watcher = AutoLogWatcher(storage)
    
    # Execute the appropriate mode
    try:
        if args.wrap:
            watcher.wrap_command(args.wrap)
        elif args.watch:
            watcher.watch_file(args.watch, args.interval)
        elif args.stdin:
            watcher.capture_stdin()
        else:
            # No mode specified, show help
            parser.print_help()
            print("\n💡 Tip: Use --wrap to capture command output automatically")
            return 0
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
