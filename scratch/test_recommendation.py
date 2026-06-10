import os
import sys

# Ensure app directory is in the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.models import Address
from app.services.recommendation_service import determine_recommendation

def run_tests():
    print("Running recommendation logic tests...")

    # Test Case 1: Merge Suggestion (Minor Typo, same house number/city/state/zip)
    addr1 = Address(
        street="123 MAIN ST",
        city="Springfield",
        state="IL",
        zip="62701",
        raw_text="123 Main St, Springfield, IL 62701"
    )
    addr2 = Address(
        street="123 MIAN ST",
        city="SPRINGFIELD",
        state="il",
        zip="62701 ",
        raw_text="123 Mian St, Springfield, IL 62701"
    )
    rec1 = determine_recommendation(addr1, addr2)
    print(f"Test 1 (MAIN vs MIAN, identical others): {rec1} (Expected: merge)")
    assert rec1 == "merge", f"Expected merge, got {rec1}"

    # Test Case 2: Not Duplicate Suggestion (House Numbers Differ)
    addr3 = Address(
        street="123 MAIN ST",
        city="Springfield",
        state="IL",
        zip="62701",
        raw_text="123 Main St, Springfield, IL 62701"
    )
    addr4 = Address(
        street="124 MAIN ST",
        city="Springfield",
        state="IL",
        zip="62701",
        raw_text="124 Main St, Springfield, IL 62701"
    )
    rec2 = determine_recommendation(addr3, addr4)
    print(f"Test 2 (123 vs 124 house number): {rec2} (Expected: not_duplicate)")
    assert rec2 == "not_duplicate", f"Expected not_duplicate, got {rec2}"

    # Test Case 3: Not Duplicate Suggestion (ZIP codes differ)
    addr5 = Address(
        street="123 MAIN ST",
        city="Springfield",
        state="IL",
        zip="62701",
        raw_text="123 Main St, Springfield, IL 62701"
    )
    addr6 = Address(
        street="123 MAIN ST",
        city="Springfield",
        state="IL",
        zip="62702",
        raw_text="123 Main St, Springfield, IL 62702"
    )
    rec3 = determine_recommendation(addr5, addr6)
    print(f"Test 3 (ZIP 62701 vs 62702): {rec3} (Expected: not_duplicate)")
    assert rec3 == "not_duplicate", f"Expected not_duplicate, got {rec3}"

    # Test Case 4: Not Duplicate Suggestion (Cities differ)
    addr7 = Address(
        street="123 MAIN ST",
        city="Springfield",
        state="IL",
        zip="62701",
        raw_text="123 Main St, Springfield, IL 62701"
    )
    addr8 = Address(
        street="123 MAIN ST",
        city="Chicago",
        state="IL",
        zip="62701",
        raw_text="123 Main St, Chicago, IL 62701"
    )
    rec4 = determine_recommendation(addr7, addr8)
    print(f"Test 4 (Springfield vs Chicago city): {rec4} (Expected: not_duplicate)")
    assert rec4 == "not_duplicate", f"Expected not_duplicate, got {rec4}"

    # Test Case 5: Not Duplicate Suggestion (Street names completely different)
    addr9 = Address(
        street="123 OAK ST",
        city="Springfield",
        state="IL",
        zip="62701",
        raw_text="123 Oak St, Springfield, IL 62701"
    )
    addr10 = Address(
        street="123 ELM ST",
        city="Springfield",
        state="IL",
        zip="62701",
        raw_text="123 Elm St, Springfield, IL 62701"
    )
    rec5 = determine_recommendation(addr9, addr10)
    print(f"Test 5 (OAK vs ELM street name): {rec5} (Expected: not_duplicate)")
    assert rec5 == "not_duplicate", f"Expected not_duplicate, got {rec5}"

    # Test Case 6: Manual Review Suggestion (Missing state field)
    addr11 = Address(
        street="123 MAIN ST",
        city="Springfield",
        state=None,
        zip="62701",
        raw_text="123 Main St, Springfield, 62701"
    )
    addr12 = Address(
        street="123 MAIN ST",
        city="Springfield",
        state="IL",
        zip="62701",
        raw_text="123 Main St, Springfield, IL 62701"
    )
    rec6 = determine_recommendation(addr11, addr12)
    print(f"Test 6 (Missing state, identical others): {rec6} (Expected: manual_review)")
    assert rec6 == "manual_review", f"Expected manual_review, got {rec6}"

    print("\nAll tests passed successfully!")

if __name__ == "__main__":
    run_tests()
