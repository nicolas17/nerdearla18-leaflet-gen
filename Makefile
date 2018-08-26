output.pdf: output.odt
	libreoffice --headless --convert-to pdf output.odt
output.odt: odt/mimetype odt/META-INF/manifest.xml odt/content.xml odt/styles.xml
	rm -f $@
	cd odt && zip -X -r ../$@ $(patsubst odt/%,%,$^)
