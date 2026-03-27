
from backend.app.music_theory import get_freq, ragam_validation, RAGAM_DB

def test_mohanam_validation():
    print("Testing Mohanam Validation...")
    # Mohanam should only allow S, R2, G3, P, D2
    valid_seq = ["S", "R2", "G3", "P", "D2", "S'"]
    invalid_seq = ["S", "R2", "G3", "M1", "P"] # Includes M1
    
    is_valid = ragam_validation(valid_seq, "Mohanam")
    is_invalid = not ragam_validation(invalid_seq, "Mohanam")
    
    print(f"Valid sequence check: {is_valid}")
    print(f"Invalid sequence check (M1 present): {is_invalid}")
    assert is_valid and is_invalid
    print("Mohanam Validation PASSED\n")

def test_kalyani_vs_shankarabharanam():
    print("Testing Kalyani vs Shankarabharanam...")
    pitch = 261.63 # C
    
    # Shankarabharanam M1
    sh_m1 = get_freq("M1", pitch, "Shankarabharanam")
    # Kalyani M2
    ka_m2 = get_freq("M2", pitch, "Kalyani")
    
    print(f"Shankarabharanam M1: {sh_m1}")
    print(f"Kalyani M2: {ka_m2}")
    
    assert sh_m1 != ka_m2
    # Ratios: M1 = 4/3, M2 = 45/32
    assert abs(sh_m1 - (pitch * 4/3)) < 0.001
    assert abs(ka_m2 - (pitch * 45/32)) < 0.001
    print("Kalyani vs Shankarabharanam PASSED\n")

def test_tara_sa():
    print("Testing Tara Sa...")
    pitch = 261.63 # C
    tara_sa = get_freq("S'", pitch, "Any")
    target = pitch * 2.0
    print(f"Base Sa: {pitch}")
    print(f"Tara Sa: {tara_sa}")
    print(f"Target: {target}")
    
    assert tara_sa == target
    assert tara_sa == 523.26
    print("Tara Sa PASSED\n")

def test_all_15_ragams():
    print("Checking if all 15 ragams are in DB...")
    ragams = list(RAGAM_DB.keys())
    print(f"Count: {len(ragams)}")
    print(f"List: {ragams}")
    assert len(ragams) == 15
    print("Ragam Count PASSED\n")

if __name__ == "__main__":
    try:
        test_mohanam_validation()
        test_kalyani_vs_shankarabharanam()
        test_tara_sa()
        test_all_15_ragams()
        print("ALL VALIDATION TESTS PASSED")
    except AssertionError as e:
        print(f"VALIDATION FAILED: {e}")
    except Exception as e:
        print(f"AN ERROR OCCURRED: {e}")
