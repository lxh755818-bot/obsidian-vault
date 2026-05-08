#!/usr/bin/env python3
"""EvoMap challenge text solver - handles Unicode homoglyphs"""
import re

def solve_challenge(challenge_text: str) -> int:
    """Parse Unicode-obfuscated math challenge and return answer."""
    # Step 1: Remove noise characters
    cleaned = challenge_text
    noise = ']^\\*|~\-/#[@'
    for c in noise:
        cleaned = cleaned.replace(c, '')
    # Remove special spaces/chars
    for c in ['\ufeff', '\u200c', '\u200b', '\u00ad', '﻿', ' ', "'"]:
        cleaned = cleaned.replace(c, '')

    # Step 2: Map homoglyphs to Latin
    homoglyphs = {
        # Cyrillic → Latin (look-alike)
        'а': 'a', 'А': 'A',
        'е': 'e', 'Е': 'E',
        'о': 'o', 'О': 'O',
        'р': 'p', 'Р': 'P',
        'с': 'c', 'С': 'C',
        'т': 't', 'Т': 'T',
        'х': 'x', 'Х': 'X',
        'у': 'y', 'У': 'Y',
        'і': 'i', 'І': 'I',
        'к': 'k', 'К': 'K',
        'м': 'm', 'М': 'M',
        'в': 'v', 'В': 'V',
        'н': 'h', 'Н': 'H',
        'г': 'r', 'Г': 'R',
        'п': 'n', 'П': 'N',
        'є': 'e', 'Є': 'E',
        'ё': 'e', 'Ё': 'E',
        'щ': 'm', 'Щ': 'M',
        'ф': 'o', 'Ф': 'O',
        'з': 'e', 'З': 'E',
        'ь': 'e', 'Ь': 'E',
        'ъ': 'k', 'Ъ': 'K',
        'й': 'n', 'Й': 'N',
        'ц': 'u', 'Ц': 'U',
        'ч': 'y', 'Ч': 'Y',
        'ю': 'io', 'Ю': 'IO',
        'я': 'r', 'Я': 'R',
        'б': '6', 'Б': '6',
        'ё': 'e',
        # Greek → Latin (look-alike)
        'о': 'o', 'О': 'O',  # Greek omicron
        'е': 'e', 'Е': 'E',  # Greek small epsilon
        'і': 'i', 'І': 'I',  # Greek iota
        'р': 'p', 'Р': 'P',  # Greek rho
        'с': 'c', 'С': 'C',  # Greek sigma
        'т': 't', 'Т': 'T',  # Greek tau
        'х': 'x', 'Х': 'X',  # Greek chi
        'у': 'u', 'У': 'Y',  # Greek upsilon
        'в': 'B', 'В': 'B',  # Greek beta
        'а': 'a', 'А': 'A',  # Greek alpha
        # Armenian (minimal mapping - these are rarely number words)
        'о': 'o', 'О': 'O',
    }

    for src, dst in homoglyphs.items():
        cleaned = cleaned.replace(src, dst)

    # Step 3: Extract text
    text = cleaned.lower()

    # Step 4: Find all number words
    word_nums = {
        'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
        'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
        'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14,
        'fifteen': 15, 'sixteen': 16, 'seventeen': 17, 'eighteen': 18,
        'nineteen': 19, 'twenty': 20, 'thirty': 30, 'forty': 40,
        'fifty': 50, 'sixty': 60, 'seventy': 70, 'eighty': 80,
        'ninety': 90, 'a': 1, 'dozen': 12, 'half': 0.5,
    }

    # Find all number words in text
    found_nums = []
    words = re.findall(r'[a-z]+', text)
    for w in words:
        if w in word_nums:
            found_nums.append(word_nums[w])

    # Also find digit numbers
    digit_nums = [int(d) for d in re.findall(r'\d+', text)]
    found_nums.extend(digit_nums)

    print(f"  Parsed: {text[:80]}")
    print(f"  Numbers found: {found_nums}")

    if not found_nums:
        return 0

    # Step 5: Determine operation from context
    has_every = 'everi' in text or 'each' in text
    has_plus = 'plus' in text or 'added' in text or 'and' in text
    has_minus = 'minus' in text or 'lost' in text or 'remov' in text or 'subtract' in text or 'donat' in text
    has_times = has_every or 'times' in text or '*' in text

    if has_times and len(found_nums) >= 2:
        # "N every M cycles" or "N each M" → multiply
        answer = found_nums[0] * found_nums[-1]
    elif has_plus and not has_minus:
        answer = sum(found_nums)
    elif has_minus:
        # First minus rest
        answer = found_nums[0] - sum(found_nums[1:])
    else:
        answer = sum(found_nums)

    return answer

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        ans = solve_challenge(sys.argv[1])
        print(f"  Answer: {ans}")
