from cleverdict import CleverDict, Expand, all_aliases
import cleverdict
import pytest
import os
from collections import UserDict
from textwrap import dedent
import json
from pathlib import Path


class Test_Initialisation:
    def test_creation_using_existing_dict(self):
        """ CleverDicts can be creates from existing dictionaries """
        x = CleverDict({"total": 6, "usergroup": "Knights of Ni"})
        assert x.total == 6
        assert x["total"] == 6
        assert x.usergroup == "Knights of Ni"
        assert x["usergroup"] == "Knights of Ni"

    def test_creation_using_existing_UserDict(self):
        """ CleverDicts can be creates from existing UserDict objects """
        u = UserDict({"total": 6, "usergroup": "Knights of Ni"})
        x = CleverDict(u)
        assert x.total == 6
        assert x["total"] == 6
        assert x.usergroup == "Knights of Ni"
        assert x["usergroup"] == "Knights of Ni"

    def test_creation_using_keyword_arguments(self):
        """ CleverDicts can be created using keyword assignment """
        x = CleverDict(created="today", review="tomorrow")
        assert x.created == "today"
        assert x["created"] == "today"
        assert x.review == "tomorrow"
        assert x["review"] == "tomorrow"

    def test_creation_using_vars(self):
        """ Works for 'simple' data objects i.e. no methods just data """

        class My_class:
            pass

        m = My_class()
        m.subject = "Python"
        x = CleverDict(vars(m))
        assert x.subject == "Python"
        assert x["subject"] == "Python"

    def test_creation_using_fromkeys(self):
        """ Works for initiating >1 keys with the same value"""
        x = CleverDict().fromkeys(["a", 1, "what?"], "val")
        assert x.a == "val"
        assert x._1 == "val"
        assert x.what_ == "val"

    def test_creation_using_list(self):
        """ Works for initiating using a list of iterables """
        x = CleverDict([(1, "one"), [2, "two"], (3, "three")])
        assert x._1 == "one"
        assert x._2 == "two"
        assert x._3 == "three"


class Test_Core_Features:
    def test_tolist(self):
        """
        Create a list of (k,v) tuples e.g. for serialising dictionaries
        with numeric keys (which isn't supported in json.dumps/.loads)
        """
        x = CleverDict({1: "one", 2: "two"})
        assert x.to_list() == [(1, "one"), (2, "two")]

    def test_use_as_dict(self):
        d = dict.fromkeys((0, 1, 23, "what?", "a"), "test")
        x = CleverDict(d)
        x.setattr_direct("b", 2)
        assert dict(x) == d

    def test_add_alias_delete_alias(self):
        """
        Aliases are created automatically after expanding 1, True
        for example.  add_alias() and delete_alias() allow us to specify
        additional attribute names as aliases, such that if the value of one
        changes, the value changes for all.
        It is not possible to delete a key.
        """
        x = CleverDict({"red": "a lovely colour", "blue": "a cool colour"})
        alias_list = ["crimson", "burgundy", "scarlet", "normalise~me"]

        x.add_alias("red", alias_list[0])
        x.add_alias("red", alias_list)
        # setting an alias that is already defined for another key is not allowed
        with pytest.raises(KeyError):
            x.add_alias("blue", alias_list[0])
        # setting via an alias is also valid
        x.add_alias("scarlet", "rood")
        assert x.rood == "a lovely colour"

        for alias in alias_list[:-1]:
            assert getattr(x, alias) == "a lovely colour"
            assert x[alias] == "a lovely colour"
        assert getattr(x, "normalise_me") == "a lovely colour"
        assert x["normalise_me"] == "a lovely colour"

        # Updating one alias (or primary Key) should update all:
        x.burgundy = "A RICH COLOUR"
        assert x.scarlet == "A RICH COLOUR"

        x.delete_alias(["scarlet"])
        with pytest.raises(AttributeError):
            x.scarlet
        assert x.crimson == "A RICH COLOUR"

        x.crimson = "the best colour of all"
        assert x.burgundy == "the best colour of all"

        with pytest.raises(KeyError):
            x.delete_alias(["scarlet"])
        # can't delete the  key element
        with pytest.raises(KeyError):
            x.delete_alias("red")

        # test 'expansion' of alias
        x.add_alias("red", True)
        assert x._True is x[True] is x._1 is x[1] is x["red"]

        x = CleverDict()
        x["2"] = 1
        x.add_alias("2", True)
        assert x.get_aliases("2") == ["2", "_2", True, "_1", "_True"]
        # removes True, '_1' and '_True'
        x.delete_alias(True)
        assert x.get_aliases("2") == ["2", "_2"]

        x = CleverDict()
        x["2"] = 1
        x.add_alias("2", True)
        assert x.get_aliases("2") == ["2", "_2", True, "_1", "_True"]
        # only remove True,not '_1' and '_True'
        with Expand(False):
            x.delete_alias(True)
        assert x.get_aliases("2") == ["2", "_2", "_1", "_True"]

    def test_value_change(self):
        """ New attribute values should update dictionary keys & vice versa """
        x = CleverDict()
        x.life = 42
        x["life"] = 43
        assert x.life == 43
        assert x["life"] == 43
        x.life = 42
        assert x.life == 42
        assert x["life"] == 42
        x["1"] = 10
        assert x["1"] == 10
        assert x["_1"] == 10
        assert x._1 == 10
        x["_1"] = 11
        assert x["1"] == 11
        assert x["_1"] == 11
        assert x._1 == 11
        x._1 = 12
        assert x["1"] == 12
        assert x["_1"] == 12
        assert x._1 == 12
        # can't double assign
        with pytest.raises(KeyError):
            x["+1"] = 1

    def test_info(self, capsys):
        global c  # globals are not 'seen' by info()
        z = b = a = c = CleverDict.fromkeys((0, 1, 2, "a", "what?", "return"), 0)
        c.add_alias(1, "one")
        c.delete_alias("_True")
        c.setattr_direct("b", "B")
        c.info()  # this prints to stdout
        out, err = capsys.readouterr()
        assert out == dedent(
            """\
CleverDict:
    a is b is z
    a[0] == a['_0'] == a['_False'] == a._0 == a._False == 0
    a[1] == a['_1'] == a['one'] == a._1 == a.one == 0
    a[2] == a['_2'] == a._2 == 0
    a['a'] == a.a == 0
    a['what?'] == a['what_'] == a.what_ == 0
    a['return'] == a['_return'] == a._return == 0
    a.b == 'B'
"""
        )
        z = b = a = c = CleverDict.fromkeys(["a"], "A")
        assert c.info(as_str=True) == "CleverDict:\n    a is b is z\n    a['a'] == a.a == 'A'"
        del a
        assert c.info(as_str=True) == "CleverDict:\n    b is z\n    b['a'] == b.a == 'A'"
        del b
        assert c.info(as_str=True) == "CleverDict:\n    z['a'] == z.a == 'A'"
        del z
        assert c.info(as_str=True) == "CleverDict:\n    x['a'] == x.a == 'A'"


class Test_Misc:
    def test_to_lines(self, tmpdir):
        d = CleverDict()
        d["zero"] = "nul"
        d["one"] = "een"
        d["two"] = "twee"
        d["three"] = "drie"
        d["four"] = "vier"
        d["five"] = "vijf"
        d["six"] = "zes"
        d["7"] = "zeven"
        assert d.to_lines() == "nul\neen\ntwee\ndrie\nvier\nvijf\nzes\nzeven"
        assert d.to_lines(start_at=4) == "vier\nvijf\nzes\nzeven"
        assert d.to_lines(start_at=10) == ""
        file_path = Path(tmpdir) / "tmp.txt"
        d.to_lines(file_path=file_path)
        with open(file_path, "r") as f:
            assert f.read() == d.to_lines()

    def test_to_json(self, tmpdir):
        d = CleverDict()
        d["zero"] = "nul"
        d["one"] = "een"
        d["two"] = "twee"
        d["three"] = "drie"
        d["four"] = "vier"
        d["five"] = "vijf"
        d["six"] = "zes"
        d[7] = "zeven"
        result = CleverDict(d)
        del result[7]
        result["7"] = "zeven"
        assert CleverDict.from_json(d.to_json()) == result

    #        assert CleverDict.from_json(d.to_json(never_save=["one"])) == eval(result.__repr__(ignore=["one"]))
    #        assert CleverDict.from_json(d.to_json(never_save=["one", 7])) == eval(result.__repr__(ignore=["one", 7]))

    def test_from_lines(self, tmpdir):
        d0 = CleverDict()
        d0[0] = "nul"
        d0[1] = "een"
        d0[2] = "twee"
        d0[3] = "drie"
        d0[4] = "vier"
        d0[5] = "vijf"
        d0[6] = "zes"
        d0[7] = "zeven"
        d10 = CleverDict({i: v for i, v in enumerate(d0.values(), start=10)})
        lines = d0.to_lines()
        assert d0 == CleverDict.from_lines(lines)
        assert d10 == CleverDict.from_lines(lines, start_at=10)

        file_path = Path(tmpdir) / "tmp.txt"
        d0.to_lines(file_path=file_path)
        d = CleverDict.from_lines(file_path=file_path)
        assert d == d0
        d = CleverDict.from_lines(file_path=file_path, start_at=10)
        assert d == d10

        with pytest.raises(ValueError):
            CleverDict.from_lines()

        with pytest.raises(ValueError):
            CleverDict.from_lines(lines=lines, file_path=file_path)

    def test_from_json(self, tmpdir):
        d = CleverDict()
        d["zero"] = "nul"
        d["one"] = "een"
        d["two"] = "twee"
        d["three"] = "drie"
        d["four"] = "vier"
        d["five"] = "vijf"
        d["six"] = "zes"
        d["7"] = "zeven"
        json_data = d.to_json()
        result = CleverDict.from_json(json_data)
        assert result == d
        file_path = Path(tmpdir) / "tmp.txt"
        d.to_json(file_path=file_path)
        result = CleverDict.from_json(file_path=file_path)
        assert d == result

        with pytest.raises(ValueError):
            CleverDict.from_json()

        with pytest.raises(ValueError):
            CleverDict.from_json(json_data=json_data, file_path=file_path)

    def test_never_save(self):
        """ CleverDict.never_save lists aliases and keys which should never be
        converted to json or saved including:

        password
        save_path
        _aliases
        """
        x = CleverDict({"password": "Top Secret", "userid": "Michael Palin"})
        x.add_alias("password", "keyphrase")
        x.autosave(silent=True)
        path = x.save_path
        lines = x.to_lines()
        for output in [x.to_json(), repr(x.to_list()), lines]:
            assert "password" not in output
            assert "Top Secret" not in output
            assert "auto_save" not in output
            assert "_aliases" not in output
            if output != lines:
                assert "userid" in output
        x.autosave(
            "off", silent=True
        )  # Ruud autosave works apparently CleverDict wise. If we do not switch it off, all other CleverDict's will also autosave. And thus many test will fail

    def test_to_and_from_json_1(self):
        """ It should be possible to completely reconstruct a CleverDict
        object, excluding _vars (attributes set directly without updating
        the dictionary) after .to_json followed by .from_json """
        d = CleverDict({"one": "een"})
        d.add_alias("one", "ONE")
        j = d.to_json(fullcopy=True)
        new_d = CleverDict.from_json(j)

        assert new_d == d

    def test_to_and_from_json_2(self):
        """ Automatically created aliases should be presevered after .to_json
        followed by .from_json """
        d = CleverDict({"#1": 1})
        j = d.to_json()
        new_d = CleverDict.from_json(j)
        assert d._1 is d["#1"]
        assert new_d._1 is new_d["#1"]
        new_d._1 += 1
        assert new_d._1 == new_d["#1"]

    def test_to_and_from_json_3(self):
        def example_user_code(clever_dict):
            """ Typical use of CleverDict is aliases to provide interchangeable
            attributes.  In this case .number and .Number.  Quite subtle and easy
            to overlook when debugging """
            clever_dict.number += 1
            return clever_dict.Number

        """ example_user_code should work equally well after .to_json followed
        by .from_json """
        d = CleverDict({"number": 1})
        d.add_alias("number", "Number")
        j = d.to_json(fullcopy=True)
        new_d = CleverDict.from_json(j)
        assert d.number == d.Number == new_d.number == new_d.Number
        assert example_user_code(d) == 2
        assert example_user_code(new_d) == 2

    def test_to_and_from_json_4(self):
        """
        Attributes created with setattr_direct are saved with fullcopy=True
        """
        d = CleverDict({1: 2, 3: 4, 0: 5, "string": 6})
        d.setattr_direct("extra", 42)
        j = d.to_json(fullcopy=True)
        new_d = CleverDict.from_json(j)
        assert new_d.extra == 42

    def test_to_and_from_json_5(self):
        """
        Aliases created with add_alias are saved with fullcopy=True
        """
        d = CleverDict({1: 2, 3: 4, 0: 5, "string": 6})
        d.add_alias(3, "nul")
        j = d.to_json(fullcopy=True)
        new_d = CleverDict.from_json(j)
        assert new_d.nul == 4

    def test_default_to_from_json(self):
        """Only data dictionary should be copied with .to_json() by default"""
        d = CleverDict({"1": 2, "3": 4, "0": 5, "string": 6})
        d.setattr_direct("extra", 42)
        d.add_alias("3", "nul")
        j = d.to_json()
        new_d = CleverDict.from_json(j)
        assert new_d.items() == d.items()
        with pytest.raises(AttributeError):
            new_d.nul
        with pytest.raises(KeyError):
            new_d["extra"]

    def test_get_default_settings_path(self):
        path = CleverDict.get_new_save_path()
        info = "test"
        with open(path, "w") as file:
            file.write(info)

        with open(path, "r") as file:
            assert file.read() == info
        path.unlink()
        assert CleverDict.get_new_save_path() != path  # when called a second time, should be different

    def test_get_app_dir(self):
        """
        tests whether the cleverdict implementation of get_app_dir is ok (can only be tested if click is installed)
        it will test only the right output on the OS the test is running on
        """
        try:
            import click
        except ModuleNotFoundError:
            pytest.skip("could not import click")
        assert click.get_app_dir("x") == cleverdict.get_app_dir("x")


class Test_Internal_Logic:
    def test_raises_error(self):
        """
        Attribute and Key errors should be raised as with normal objects/dicts
        """
        x = CleverDict()
        with pytest.raises(AttributeError):
            x.a
        with pytest.raises(KeyError):
            x["a"]

    def test_conversions(self):
        x = CleverDict({1: "First Entry", " ": "space", "??": "question"})
        assert x._1 == "First Entry"
        assert x["_1"] == "First Entry"
        assert x[1] == "First Entry"
        with pytest.raises(KeyError):
            x["1"] = 5
        with pytest.raises(KeyError):
            x = CleverDict({1: "First Entry", "1": "space", "??": "question"})
        x["else"] = "is else"
        assert x["else"] == "is else"
        assert x["_else"] == "is else"
        assert x._else == "is else"
        with pytest.raises(KeyError):
            x["?else"] = "other"
        x._4 = "abc"
        with pytest.raises(KeyError):
            x["4"] = "def"
        x[12345.0] = "klm"
        assert x._12345 == "klm"
        x[2.0] = "two-point-0"
        assert x._2 == "two-point-0"
        x["11a23bccà~£#@q123b/=€впВМвапрй"] = "abc"
        assert x._11a23bccà____q123b___впВМвапрй == "abc"
        assert x["11a23bccà~£#@q123b/=€впВМвапрй"] == "abc"
        assert x["_11a23bccà____q123b___впВМвапрй"] == "abc"

    def test_data_attribute(self):
        x = CleverDict()
        x["data"] = "data"
        assert x["data"] == "data"
        assert x.data == "data"

    def test_normalise_unicode(self):
        """
        Most unicode letters are valid in attribute names
        """
        x = CleverDict({"ветчина_и_яйца$a": "ham and eggs"})
        x.ве = "ve"
        x["1ве"] = "1ve"
        assert x.ветчина_и_яйца_a == "ham and eggs"
        assert x.ве == "ve"
        assert x._1ве == "1ve"

    def test_True_False_None_functionality(self):
        """
        When setting dictionary keys in Python:
        d[0] is d[0.0] is d[False]
        d[1] is d[1.0] is d[True]
        d[1234.0] is d[1234]
        If the same key is set in different ways e.g.
            d = {0: "Zero", False: "Untrue"}
        the last (rightmost) value overwrites any previous values, so
            d[0] == "Untrue"
        Furthermore, keywords like True and False can't be used as attributes.
        """
        x = CleverDict()
        x[0] = 0
        x[False] = 1
        x[1] = 2
        x[True] = 3
        x[None] = "nothing"
        assert x[0] == 1
        assert x[False] == 1
        assert x["_0"] == 1
        assert x["_False"] == 1
        assert x._0 == 1
        assert x._False == 1
        assert x[1] == 3
        assert x[True] == 3
        assert x["_1"] == 3
        assert x["_True"] == 3
        assert x._1 == 3
        assert x._True == 3
        assert x[None] == "nothing"
        assert x["_None"] == "nothing"
        with pytest.raises(KeyError):
            x["None"]

    def test_repr_and_eq(self):
        """
        Tests that the output from __repr__ can be used to reconstruct the
        CleverDict object, and __eq__ can be used to compare CleverDict objects."""
        x = CleverDict()
        x[0] = 0
        x[False] = 1
        x[1] = 2
        x[True] = 3
        x.a = 4
        x["what?"] = 5
        x.add_alias("a", "c")
        y = eval(repr(x))
        assert x == y
        y.b = 6
        assert x != y
        x = CleverDict()
        assert eval(repr(x)) == x
        with Expand(False):
            x = CleverDict({True: 1})
            assert len(x.get_aliases()) == 1
            assert CleverDict(eval(repr(x))) == x
            # check whether _expand has been properly reset
            x = CleverDict({True: 1})
            assert len(x.get_aliases()) == 1
        # empty dict with one variable
        x = CleverDict()
        x.setattr_direct("a", 1)
        assert len(x.get_aliases()) == 0
        assert eval(repr(x)) == x

    def testupdate(self):
        x = CleverDict.fromkeys((0, 1, 2, "a", "what?", "return"), 0)
        y = CleverDict({0: 2, "c": 3})
        x.update(y)
        assert x == CleverDict({0: 2, 1: 0, 2: 0, "a": 0, "what?": 0, "return": 0, "c": 3})

    def test_del(self):
        """ __delattr__ should delete dict items regardless of alias """
        x = CleverDict()
        x[1] = 1
        del x[1]
        with pytest.raises(KeyError):
            x[1]
        x[1] = 1
        del x["_1"]
        with pytest.raises(KeyError):
            x[1]
        x[1] = 1
        del x._1
        with pytest.raises(KeyError):
            x[1]
        with pytest.raises(KeyError):
            del x[1]
        with pytest.raises(AttributeError):
            del x._1

    def test_del_with_setattr_direct(self):
        """ __delattr__ should delete attributes created with setattr_direct"""
        x = CleverDict()
        x.setattr_direct("direct_variable", "direct_value")
        assert hasattr(x, "direct_variable")
        del x.direct_variable
        assert not hasattr(x, "direct_variable")

    def testget_key(self):
        x = CleverDict.fromkeys(("a", 0, 1, "what?"), 1)
        x.add_alias(0, "zero")
        for key in x.keys():
            for name in x.get_aliases(key):
                assert x.get_key(name) == key
        assert x.get_key(True) == 1
        assert x.get_key("_True") == 1
        assert x.get_key("zero") == 0

    def test_Expand(self):
        with Expand(False):
            x = CleverDict.fromkeys(("a", 0, 1, "what?"), 1)
            x.add_alias(0, 2)
        assert x.get_aliases("a") == ["a"]
        assert x.get_aliases(0) == [0, 2]
        assert x.get_aliases(1) == [1]

        x = CleverDict.fromkeys(("a", 0, 1, "what?"), 1)
        x.add_alias(0, 2)
        assert x.get_aliases("a") == ["a"]
        assert x.get_aliases(0) == [0, "_0", "_False", 2, "_2"]
        assert x.get_aliases(1) == [1, "_1", "_True"]

        with Expand(True):
            x = CleverDict.fromkeys(("a", 0, 1, "what?"), 1)
            x.add_alias(0, 2)
        assert x.get_aliases("a") == ["a"]
        assert x.get_aliases(0) == [0, "_0", "_False", 2, "_2"]
        assert x.get_aliases(1) == [1, "_1", "_True"]

        CleverDict.expand = False
        x = CleverDict({1: 1})
        with pytest.raises(AttributeError):
            x._1
        CleverDict.expand = True
        x = CleverDict({1: 1})
        x._1

    def test_expand_context_manager(self):
        with Expand(False):
            assert not CleverDict.expand
        assert CleverDict.expand
        with Expand(True):
            assert CleverDict.expand
        assert CleverDict.expand

        CleverDict.expand = False
        with Expand(False):
            assert not CleverDict.expand

        assert not CleverDict.expand
        with Expand(True):
            assert CleverDict.expand
        assert not CleverDict.expand

        CleverDict.expand = True

    def test_all_aliases(self):
        assert all_aliases("a") == ["a"]
        assert all_aliases(True) == [True, "_1", "_True"]
        assert all_aliases("3test test") == ["3test test", "_3test_test"]
        with Expand(False):
            assert all_aliases("a") == ["a"]
            assert all_aliases(True) == [True]
            assert all_aliases("3test test") == ["3test test"]

    def test_setattr_direct(self):
        """
        Sets an attribute directly, i.e. without making it into an item.
        Attributes set via setattr_direct will
        expressly not appear in the result of repr().  They will appear in the result of str() however.
        """
        x = CleverDict()
        x.setattr_direct("a", "A")
        assert x.a == "A"
        with pytest.raises(KeyError):
            x["a"]
            x.get_key("a")
        assert x.get_aliases() == []


#    def test_version(self):
#        assert isinstance(__version__, str)


def example_save_function(self, key, value):
    """
    Example of a custom function which can be called by self._save()
    whenever the value of a CleverDict instance is created or changed.
    Required arguments are: self, name: any and value: any
    Specify this (or any other) function as the default 'save' function as follows:
    CleverDict.save = example_save_function
    """
    output = f"Notional save to database: .{key} = {value} {type(value)}"
    with open("example.log", "a") as file:
        file.write(output + "\n")


#    print(output)


def dummy_save_function(self, *args, **kwargs):
    pass


class Test_Save_Functionality:
    def delete_log(self):
        try:
            os.remove("example.log")
        except FileNotFoundError:
            pass

    def test_save_on_creation(self):
        """ Once set, CleverDict.save should be called on creation """
        CleverDict.save = example_save_function
        self.delete_log()
        CleverDict({"total": 6, "usergroup": "Knights of Ni"})
        with open("example.log", "r") as file:
            log = file.read()
        assert (
            log
            == """Notional save to database: .total = 6 <class 'int'>\nNotional save to database: .usergroup = Knights of Ni <class 'str'>\n"""
        )
        self.delete_log()
        CleverDict.save = dummy_save_function

    def test_save_onupdate(self):
        """ Once set, CleverDict.save should be called after updates """
        x = CleverDict({"total": 6, "usergroup": "Knights of Ni"})
        self.delete_log()
        CleverDict.save = example_save_function
        x.total += 1
        with open("example.log", "r") as file:
            log = file.read()
        assert log == "Notional save to database: .total = 7 <class 'int'>\n"
        self.delete_log()
        CleverDict.save = dummy_save_function

    def test_save_misc(self):
        class SaveDict(CleverDict):
            def __init__(self, *args, **kwargs):
                self.setattr_direct("store", [])
                super().__init__(*args, **kwargs)

            def save(self, name, value):
                self.store.append((name, value))

        x = SaveDict({"a": 1, 2: 2})
        x.b = 3
        x["c"] = 4
        x[3] = 5
        x._3 = 6
        x[3] = 7
        x["_3"] = 8
        try:
            x["?3"] = 9
        except KeyError:
            pass
        x._4 = 9
        x["_4"] = 10
        try:
            x["4"] = 11
        except KeyError:
            pass
        assert x.store == [("a", 1), (2, 2), ("b", 3), ("c", 4), (3, 5), (3, 6), (3, 7), (3, 8), ("_4", 9), ("_4", 10)]


def example_delete_function(self, key):
    pass


#    print(f"Notionally deleting '{key}''")


class Test_Delete_Functionality:
    def delete_log(self):
        try:
            os.remove("example.log")
        except FileNotFoundError:
            pass

    def test_auto_delete(self):
        """ Once set, CleverDict.save should be called on creation """
        CleverDict.delete = example_delete_function
        self.delete_log()
        CleverDict({"total": 6, "usergroup": "Knights of Ni"})
        CleverDict.save = dummy_save_function


if __name__ == "__main__":
    pytest.main(["-vv", "-s"])
