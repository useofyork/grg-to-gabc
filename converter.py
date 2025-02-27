from os import listdir, mkdir
import io
import re

def bytes_from_file(filename, chunksize=8192):
    with open(filename, "rb") as f:
        while True:
            chunk = f.read(chunksize)
            if chunk:
                for b in chunk:
                    yield b
            else:
                break

offsets_lc = "mlkjihgfedcba"
offsets_uc = "MLKJIHGFEDCBA"

lookup_specials = {}
lookup_notes = {}
lookup_ignore = {}
with open("lookup-table.txt", "r") as myfile:
    for lookup_line in myfile.readlines():
        parts = lookup_line.strip().split()
        if parts[1] == "n":
            lookup_notes[int(parts[0])] = parts[2]
        if parts[1] == "s":
            lookup_specials[int(parts[0])] = parts[2]
        if parts[1] == "x":
            lookup_ignore[int(parts[0])] = True

def process_file(input_filename):
    raw = []
    for b in bytes_from_file("input/" + input_filename):
        # Python 3 change
        # OLD: raw += [ord(b)]
        # TypeError: ord() expected string of length 1, but int found 
        # NEW:
        raw += [b]

    stringified = "-".join([str(r) for r in raw[41:]])
    # split raw byte data into elements at any of these six-byte markers
    items = re.split("-0-94-222-78-0-255-|-1-94-222-78-0-255-|-2-94-222-78-0-255-|-3-94-222-78-0-255-|-4-94-222-78-0-255-", stringified)

    drop_cap = ""
    outputs = []

    for item in items:
        item_bytes = [int(b) for b in item.split("-")]

        lookup_code = item_bytes[3]

        # Python 3
        # integer division stops a TypeError later
        offset = item_bytes[5] // 6
        
        if lookup_code == 105 or lookup_code == 200:
            try:
                
                annotation_a = ""
                annotation_a_index = 32
                while item_bytes[annotation_a_index] != 0:
                    annotation_a += chr(item_bytes[annotation_a_index])
                    annotation_a_index += 1

                annotation_b = ""
                annotation_b_index = 66
                while item_bytes[annotation_b_index] != 0:
                    annotation_b += chr(item_bytes[annotation_b_index])
                    annotation_b_index += 1

                drop_cap_index = 100
                while item_bytes[drop_cap_index] != 0:
                    drop_cap += chr(item_bytes[drop_cap_index])
                    drop_cap_index += 1

                if annotation_a != "" or annotation_b != "" or drop_cap != "":
                    outputs += [{"annotation_a": annotation_a, "annotation_b": annotation_b, "objects": []}]
                
                lookup_code = item_bytes[120]
                # integer division
                offset = item_bytes[122] // 6
            except:
                continue # Not marking a new file

        if lookup_code == 6:
            outputs[-1]["objects"] += [{"text": "", "meta": {8: "c1", 6: "c2", 4: "c3", 2: "c4"}[offset], "space": False, "special": True}]
            continue

        if lookup_code == 7:
            outputs[-1]["objects"] += [{"text": "", "meta": {8: "f1", 6: "f2", 4: "f3", 2: "f4"}[offset], "space": False, "special": True}]
            continue

        text = u""
        if len(drop_cap) > 0:
            text += drop_cap
            drop_cap = ""
        text_index = 13
        while item_bytes[text_index] != 0:
            # the diacritic code doesn't seem necessary...
            # but don't copy hyphen (Gregorio does it), or dagger, dbldagger since they err
            if item_bytes[text_index] not in [45, 134, 135]:
                text += chr(item_bytes[text_index])
            text_index += 1

        meta = None
        special = False

        if lookup_code in lookup_notes:
            offset_min = 12
            for char in lookup_notes[lookup_code]:
                offset_lc = offsets_lc.find(char)
                offset_uc = offsets_uc.find(char)
                if offset_lc >= 0 and offset_lc < offset_min:
                    offset_min = offset_lc
                if offset_uc >= 0 and offset_uc < offset_min:
                    offset_min = offset_uc
            meta = ""
            for char in lookup_notes[lookup_code]:
                offset_lc = offsets_lc.find(char)
                offset_uc = offsets_uc.find(char)
                if offset_lc >= 0 and offset <= offset_min:
                    # Python 3
                    # previous integer divisions for offset stops a TypeError here
                    meta += offsets_lc[offset_lc - offset_min + offset]
                elif offset_uc >= 0 and offset <= offset_min:
                    # Python 3
                    # ditto
                    meta += offsets_uc[offset_uc - offset_min + offset]
                else:
                    meta += char

        if lookup_code in lookup_specials:
            meta = lookup_specials[lookup_code]
            special = True

        if lookup_code in lookup_ignore:
            continue

        if meta == None:
            # Python 3
            # print needs ()
            print(" - Needs lookup for code " + str(lookup_code))
            meta = "<<<LOOKUP " + str(lookup_code) + ">>>"

        obj = {"text": text.strip(), "meta": meta, "space": text[-1] == " " if len(text) > 0 else False, "special": special}

        outputs[-1]["objects"] += [obj]

    for output_index, output in enumerate(outputs):
        # added semicolon to end the header lines
        result = "annotation: " + output["annotation_a"] + ";" + "\nannotation: " + output["annotation_b"] + ";" + "\n%%\n"

        acc_spaces = 0
        acc_meta = []
        for obj in output["objects"]:
            if len(obj["text"]) > 0:
                if len(acc_meta) > 0:
                    # put an inter neume spacer here if desired, "/", "!", etc.
                    result += "(" + "".join(acc_meta) + ")"
                    acc_meta = []
                if acc_spaces > 0:
                    result += acc_spaces * " "
                    acc_spaces = 0
                result += obj["text"]

            if obj["special"]:
                if len(acc_meta) > 0:
                    result += "(" + "".join(acc_meta) + ")"
                    acc_meta = []
                # added a newline after all specials
                result += " (" + obj["meta"] + ")\n"
            else:
                acc_meta += [obj["meta"]]

            if obj["space"]:
                acc_spaces += 1

        output_filename = "output/" + input_filename.replace(".GRG", ".gabc").replace(".grg", ".gabc")
        if len(outputs) > 1:
            output_filename = output_filename.replace(".gabc", "-" + str(output_index + 1) + ".gabc")

        with io.open(output_filename, "w", encoding="utf-8") as output_file:
            output_file.write(result.replace("\n ", "\n"))
            # Python 3
            # print needs ()
            print(" - Wrote " + output_filename)

if __name__ == "__main__":
    input_filenames = listdir("input")

    try:
        mkdir("output")
    except:
        pass

    for input_filename in input_filenames:
        if input_filename in [".DS_Store"]:
            continue
        # Python 3
        # print needs ()s
        print("Processing " + input_filename)
        process_file(input_filename)
