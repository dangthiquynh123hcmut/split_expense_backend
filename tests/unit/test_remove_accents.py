"""
Unit tests for utils.functions.remove_accents.remove_accents.

Pure string function — no database or Django dependency.
"""

from utils.functions.remove_accents import remove_accents


class TestRemoveAccents:
    # ------------------------------------------------------------------
    # Basic sanity
    # ------------------------------------------------------------------

    def test_plain_ascii_is_unchanged_except_lowercase(self):
        assert remove_accents("hello") == "hello"

    def test_uppercase_is_lowercased(self):
        assert remove_accents("HELLO") == "hello"

    def test_empty_string_returns_empty(self):
        assert remove_accents("") == ""

    # ------------------------------------------------------------------
    # Individual vowel families
    # ------------------------------------------------------------------

    def test_a_variants_normalized(self):
        # àáạảãâầấậẩẫăằắặẳẵ → a
        input_text = "àáạảãâầấậẩẫăằắặẳẵ"
        result = remove_accents(input_text)
        assert result == "a" * len(input_text)

    def test_e_variants_normalized(self):
        input_text = "èéẹẻẽêềếệểễ"
        result = remove_accents(input_text)
        assert result == "e" * len(input_text)

    def test_i_variants_normalized(self):
        input_text = "ìíịỉĩ"
        result = remove_accents(input_text)
        assert result == "i" * len(input_text)

    def test_o_variants_normalized(self):
        input_text = "òóọỏõôồốộổỗơờớợởỡ"
        result = remove_accents(input_text)
        assert result == "o" * len(input_text)

    def test_u_variants_normalized(self):
        input_text = "ùúụủũưừứựửữ"
        result = remove_accents(input_text)
        assert result == "u" * len(input_text)

    def test_y_variants_normalized(self):
        input_text = "ỳýỵỷỹ"
        result = remove_accents(input_text)
        assert result == "y" * len(input_text)

    def test_d_with_stroke_normalized(self):
        assert remove_accents("đ") == "d"
        assert remove_accents("Đ") == "d"

    # ------------------------------------------------------------------
    # Full Vietnamese words / names
    # ------------------------------------------------------------------

    def test_full_vietnamese_name(self):
        assert remove_accents("Nguyễn Văn An") == "nguyen van an"

    def test_full_name_with_mixed_accents(self):
        result = remove_accents("Trần Thị Bích Ngọc")
        assert result == "tran thi bich ngoc"

    def test_city_name(self):
        assert remove_accents("Hồ Chí Minh") == "ho chi minh"

    def test_common_phrase(self):
        result = remove_accents("xin chào thế giới")
        assert result == "xin chao the gioi"

    # ------------------------------------------------------------------
    # Edge cases
    # ------------------------------------------------------------------

    def test_numbers_and_special_chars_pass_through(self):
        result = remove_accents("abc123!@#")
        assert result == "abc123!@#"

    def test_spaces_preserved(self):
        result = remove_accents("a b c")
        assert result == "a b c"
