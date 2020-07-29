all: build

rpm-el7:
	@rm -fr rpmbuild/el7
	@mkdir -p rpmbuild/el7/RPMS rpmbuild/el7/SPECS \
	  rpmbuild/el7/SRPMS \
	  rpmbuild/el7/BUILD/etc/cloud/cloud.cfg.d \
	  rpmbuild/el7/BUILD/usr/lib/python2.7/site-packages/cloudinit/sources
	docker build -f Dockerfile.rpmbuild -t rpmbuild:el7 .
	docker run --rm -it \
		-v $$(pwd)/rpmmacros:/root/.rpmmacros:ro \
		-v $$(pwd)/rpmbuild/el7:/root/rpmbuild \
		-v $$(pwd)/rpm.el7.spec:/root/rpmbuild/SPECS/rpm.spec:ro \
		-v $$(pwd)/99-DataSourceVMwareGuestInfo.cfg:/root/rpmbuild/BUILD/etc/cloud/cloud.cfg.d/99-DataSourceVMwareGuestInfo.cfg:ro \
		-v $$(pwd)/DataSourceVMwareGuestInfo.py:/root/rpmbuild/BUILD/usr/lib/python2.7/site-packages/cloudinit/sources/DataSourceVMwareGuestInfo.py:ro \
		-v $$(pwd)/dscheck_VMwareGuestInfo.sh:/root/rpmbuild/BUILD/usr/bin/dscheck_VMwareGuestInfo:ro \
		rpmbuild:el7 \
		rpmbuild -ba /root/rpmbuild/SPECS/rpm.spec

rpm: rpm-el7

build: rpm
