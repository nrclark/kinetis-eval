.PHONY: output
	
output: kinetis.kicad_pcb express_pcb_allowed_holes.txt
	mkdir -p $@
	rm -f $@/*
	scripts/generate_drills.py $< -o $@ -c express_pcb_allowed_holes.txt 
	scripts/generate_gerbers.py $< -o $@
