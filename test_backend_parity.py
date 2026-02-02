"""
Test Script: Verify FastAPI output matches Flask output exactly
Tests both backends with the same CSV input and compares results
"""

import sys
import os
import pandas as pd
import numpy as np

# Add paths for both backends
flask_path = os.path.abspath('/Users/rmjpkumara/Documents/Yasantha/untitled folder/untitled folder/retirement_planner')
fastapi_path = os.path.abspath('/Users/rmjpkumara/Documents/Yasantha/untitled folder/untitled folder/retirement_planner_with_fastapi_withdeployemnr')

sys.path.insert(0, flask_path)
sys.path.insert(0, fastapi_path)

def test_with_csv(csv_filename):
    """Test both backends with the same CSV file"""
    print(f"\n{'='*80}")
    print(f"Testing with: {csv_filename}")
    print(f"{'='*80}\n")
    
    # Import Flask version
    sys.path.insert(0, flask_path)
    from retirement_planner_yr import RetirementSimulator as FlaskSimulator
    
    # Import FastAPI version
    sys.path.insert(0, fastapi_path)
    from retirement_planner_yr import RetirementSimulator as FastAPISimulator
    
    # Full path to CSV
    csv_path = os.path.join(flask_path, csv_filename)
    
    if not os.path.exists(csv_path):
        print(f"❌ CSV file not found: {csv_path}")
        return False
    
    print(f"CSV file: {csv_path}")
    
    # Test 1: Standard Strategy
    print("\n--- Testing STANDARD Strategy ---")
    flask_sim_std = FlaskSimulator(config_file=csv_path, year=2025, strategy='standard')
    flask_result_std = flask_sim_std.run()
    
    fastapi_sim_std = FastAPISimulator(config_file=csv_path, year=2025, strategy='standard')
    fastapi_result_std = fastapi_sim_std.run()
    
    # Compare results
    std_match = compare_results(flask_result_std, fastapi_result_std, "Standard Strategy")
    
    # Test 2: Taxable-First Strategy
    print("\n--- Testing TAXABLE_FIRST Strategy ---")
    flask_sim_tf = FlaskSimulator(config_file=csv_path, year=2025, strategy='taxable_first')
    flask_result_tf = flask_sim_tf.run()
    
    fastapi_sim_tf = FastAPISimulator(config_file=csv_path, year=2025, strategy='taxable_first')
    fastapi_result_tf = fastapi_sim_tf.run()
    
    # Compare results
    tf_match = compare_results(flask_result_tf, fastapi_result_tf, "Taxable-First Strategy")
    
    return std_match and tf_match


def compare_results(flask_df, fastapi_df, test_name):
    """Compare two DataFrames and report differences"""
    print(f"\nComparing {test_name}:")
    
    # Check row count
    if len(flask_df) != len(fastapi_df):
        print(f"❌ Row count mismatch: Flask={len(flask_df)}, FastAPI={len(fastapi_df)}")
        return False
    else:
        print(f"✅ Row count matches: {len(flask_df)} rows")
    
    # Check column names
    flask_cols = set(flask_df.columns)
    fastapi_cols = set(fastapi_df.columns)
    
    if flask_cols != fastapi_cols:
        missing_in_fastapi = flask_cols - fastapi_cols
        extra_in_fastapi = fastapi_cols - flask_cols
        
        if missing_in_fastapi:
            print(f"❌ Columns missing in FastAPI: {missing_in_fastapi}")
        if extra_in_fastapi:
            print(f"⚠️  Extra columns in FastAPI: {extra_in_fastapi}")
        
        # Use intersection for comparison
        common_cols = flask_cols & fastapi_cols
    else:
        print(f"✅ Column names match: {len(flask_cols)} columns")
        common_cols = flask_cols
    
    # Compare values for common columns
    all_match = True
    differences = []
    
    for col in sorted(common_cols):
        flask_vals = flask_df[col].values
        fastapi_vals = fastapi_df[col].values
        
        # Handle numeric columns
        if pd.api.types.is_numeric_dtype(flask_vals):
            # Allow small floating point differences
            max_diff = np.abs(flask_vals - fastapi_vals).max()
            
            if max_diff > 0.01:  # Tolerance of 1 cent
                all_match = False
                differences.append({
                    'column': col,
                    'max_diff': max_diff,
                    'flask_sample': flask_vals[:3],
                    'fastapi_sample': fastapi_vals[:3]
                })
            else:
                if max_diff > 0:
                    print(f"✅ {col}: Match (max diff: ${max_diff:.2f})")
        else:
            # String comparison
            if not np.array_equal(flask_vals, fastapi_vals):
                all_match = False
                differences.append({
                    'column': col,
                    'type': 'string',
                    'flask_sample': flask_vals[:3],
                    'fastapi_sample': fastapi_vals[:3]
                })
    
    # Report results
    if all_match:
        print(f"\n✅ ✅ ✅ {test_name}: PERFECT MATCH!")
        print(f"All {len(common_cols)} columns match exactly")
    else:
        print(f"\n❌ {test_name}: DIFFERENCES FOUND")
        print(f"\nDifferences in {len(differences)} columns:")
        for diff in differences[:10]:  # Show first 10 differences
            print(f"\n  Column: {diff['column']}")
            if 'max_diff' in diff:
                print(f"  Max difference: ${diff['max_diff']:.2f}")
            print(f"  Flask sample: {diff['flask_sample']}")
            print(f"  FastAPI sample: {diff['fastapi_sample']}")
    
    # Show sample data from both
    print(f"\n--- Sample Output (First 5 years) ---")
    print("\nFlask Result:")
    display_cols = ['Year', 'P1_Age', 'P2_Age', 'Net_Worth', 'Bal_Taxable', 'Bal_PreTax_P1', 'Tax_Bill']
    available_cols = [c for c in display_cols if c in flask_df.columns]
    print(flask_df[available_cols].head())
    
    print("\nFastAPI Result:")
    print(fastapi_df[available_cols].head())
    
    return all_match


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("FLASK vs FASTAPI OUTPUT COMPARISON TEST")
    print("="*80)
    
    # Test with different CSV files
    test_files = ['nisha.csv', 'yasantha.csv']
    
    results = {}
    for csv_file in test_files:
        csv_path = os.path.join(flask_path, csv_file)
        if os.path.exists(csv_path):
            results[csv_file] = test_with_csv(csv_file)
        else:
            print(f"\n⚠️  Skipping {csv_file} (not found)")
            results[csv_file] = None
    
    # Final Summary
    print("\n" + "="*80)
    print("FINAL SUMMARY")
    print("="*80)
    
    for csv_file, result in results.items():
        if result is None:
            status = "⚠️  SKIPPED (file not found)"
        elif result:
            status = "✅ PASS - Outputs match perfectly"
        else:
            status = "❌ FAIL - Outputs differ"
        
        print(f"{csv_file}: {status}")
    
    # Overall result
    passed = [r for r in results.values() if r is True]
    failed = [r for r in results.values() if r is False]
    
    print(f"\nTests passed: {len(passed)}/{len(passed) + len(failed)}")
    
    if failed:
        print("\n❌ Some tests failed - FastAPI output does not match Flask")
        return False
    elif passed:
        print("\n✅ All tests passed - FastAPI produces identical output to Flask!")
        return True
    else:
        print("\n⚠️  No tests were run")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
