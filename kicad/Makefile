PCB_PROJECT := kinetis.kicad_pcb
HOLE_WHITELIST := express_pcb_allowed_holes.txt 
OUTPUT_ZIP := kinetis.zip
WORK_DIR := output

DESIGN_BASE := $(basename $(PCB_PROJECT))
ZIPPED_FILE_EXTS := gtl gbl gts gbs gto gbo gko xln
ZIPPED_FILES := $(foreach x,$(ZIPPED_FILE_EXTS),$(WORK_DIR)/$(DESIGN_BASE).$(x))

KICAD_OUTPUT_EXTS := -CuTop.gbr -CuBottom.gbr -MaskTop.gbr -MaskBottom.gbr
KICAD_OUTPUT_EXTS += -SilkTop.gbr -SilkBottom.gbr -EdgeCuts.gbr

all: $(OUTPUT_ZIP)

$(OUTPUT_ZIP): $(ZIPPED_FILES)
	rm -f $@
	zip -9TD $(abspath $@) $(abspath $^)

%.gtl: %-CuTop.gbr
	cp $< $@

%.gbl: %-CuBottom.gbr
	cp $< $@

%.gts: %-MaskTop.gbr
	cp $< $@

%.gbs: %-MaskBottom.gbr
	cp $< $@

%.gto: %-SilkTop.gbr
	cp $< $@

%.gbo: %-SilkBottom.gbr
	cp $< $@

%.gko: %-EdgeCuts.gbr
	cp $< $@

%.xln: %-PTH.drl
	cp $< $@

$(foreach x,$(KICAD_OUTPUT_EXTS),%$(x)): $(PCB_PROJECT)
	mkdir -p $(dir $@)
	rm -f $@
	scripts/generate_gerbers.py $< -o $(WORK_DIR)

%-PTH.drl: $(PCB_PROJECT) $(HOLE_WHITELIST)
	mkdir -p $(dir $@)
	rm -f $@
	scripts/generate_drills.py $< -o $(dir $@) -c $(HOLE_WHITELIST)

clean:
	rm -rf $(WORK_DIR)
	rm -f $(OUTPUT_ZIP)
