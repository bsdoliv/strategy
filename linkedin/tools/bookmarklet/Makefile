DATAPATH=${PWD}/../../data

compile: qxgrab.url.txt qxvprobe/qxvprobe.url.txt qxdprobe/qxdprobe.url.txt

%.url.txt: %.js compile.py
	python3 compile.py < $< > $@.new && \
		mv $@.new $@ 

audit2:
	python3 qxaudit.py \
		${DATAPATH}/linkedin \
		${DATAPATH}/linkedin-lote-01.txt

audit:
	python3 qxaudit.py \
		${DATAPATH}/linkedin \
		${DATAPATH}/linkedin-pack.txt

genpack:
	awk -F, '{ print  $$NF }'  < ${DATAPATH}/linkedin-pendentes.csv | grep ^http > pack.txt
	cp -v pack.txt ${DATAPATH}/linkedin-pack.txt

clean:
	rm -fv qxgrab.url.txt
	rm -fv qxvprobe/qxvprobe.url.txt
	rm -fv qxdprobe/qxdprobe.url.txt
	rm -fv *.new

#DRY=--dry
runqxvideo:
	python3 ${PWD}/qxvideo/qxvideo.py ${DRY} --dir ${PWD}/linkedin
