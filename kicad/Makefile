#--------------------------- Design-Specific Variables ------------------------#

PCB_PROJECT := kinetis.kicad_pcb
HOLE_WHITELIST := express_pcb_allowed_holes.txt 
OUTPUT_ZIP := kinetis.zip
WORK_DIR := output

#-------------------------- Derived/Constant Variables ------------------------#

DESIGN_BASE := $(basename $(PCB_PROJECT))
ZIPPED_FILE_EXTS := .gtl .gbl .gts .gbs .gto .gbo .gko .xln .gtp
ZIPPED_FILES := $(foreach x,$(ZIPPED_FILE_EXTS),$(WORK_DIR)/$(DESIGN_BASE)$(x))

KICAD_OUTPUT_EXTS := -CuTop.gbr -CuBottom.gbr -MaskTop.gbr -MaskBottom.gbr
KICAD_OUTPUT_EXTS += -SilkTop.gbr -SilkBottom.gbr -EdgeCuts.gbr -PasteTop.gbr
all: $(OUTPUT_ZIP)

#------------------------- Makefile Magic 'Pair' Macro ------------------------#

# This section creates a 'pair' macro that can be used to pair create
# simple 'copy' pattern-rules.

define _pair
%$1: %$2
	cp $$< $$@
endef
pair = $(eval $(call _pair,$1,$2))

#-------------------------------- Primary Rules -------------------------------#

$(call pair,.gtl,-CuTop.gbr)
$(call pair,.gbl,-CuBottom.gbr)
$(call pair,.gts,-MaskTop.gbr)
$(call pair,.gbs,-MaskBottom.gbr)
$(call pair,.gto,-SilkTop.gbr)
$(call pair,.gbo,-SilkBottom.gbr)
$(call pair,.gko,-EdgeCuts.gbr)
$(call pair,.gtp,-PasteTop.gbr)
$(call pair,.xln,-PTH.drl)

gerber: $(foreach x,$(KICAD_OUTPUT_EXTS),$(WORK_DIR)/$(DESIGN_BASE)$(x))
drill: $(WORK_DIR)/$(DESIGN_BASE)-PTH.drl

$(foreach x,$(KICAD_OUTPUT_EXTS),%$(x)): $(PCB_PROJECT)
	mkdir -p $(dir $@)
	rm -f $@
	scripts/generate_gerbers.py $< -o $(dir $@)

%-PTH.drl: $(PCB_PROJECT) $(HOLE_WHITELIST)
	mkdir -p $(dir $@)
	rm -f $@
	scripts/generate_drills.py $< -o $(dir $@) -c $(HOLE_WHITELIST)

$(OUTPUT_ZIP): $(ZIPPED_FILES)
	rm -f $@
	zip -9TDj $(abspath $@) $(abspath $^)

clean:
	rm -rf $(WORK_DIR)
	rm -f $(OUTPUT_ZIP)
