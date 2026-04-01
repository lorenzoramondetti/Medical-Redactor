
import unittest
import sys
import os

def run():
    # Force current directory to be in path
    sys.path.insert(0, os.getcwd())
    
    loader = unittest.TestLoader()
    suite = loader.discover('tests', pattern='test_*.py')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return exit code based on success
    sys.exit(not result.wasSuccessful())

if __name__ == '__main__':
    run()
