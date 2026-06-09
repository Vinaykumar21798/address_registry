import re
import usaddress


def extract_addresses(text):
    addresses = []
    normalized_set = set()

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    for i in range(len(lines)):
        for j in range(i + 1, min(i + 4, len(lines))):
            candidate = " ".join(lines[i:j + 1])

            try:
                parsed, _ = usaddress.tag(candidate)

                if (
                    "AddressNumber" in parsed
                    and "StreetName" in parsed
                    and "StateName" in parsed
                ):
                    normalized = " ".join(candidate.split())
                    
                    if normalized not in normalized_set:
                        normalized_set.add(normalized)
                        addresses.append(candidate)

            except Exception:
                pass

    return addresses