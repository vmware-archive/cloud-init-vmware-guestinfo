all: build

build:
	@mkdir -p rpmbuild/RPMS rpmbuild/SPECS rpmbuild/SRPMS \
	  rpmbuild/BUILD/etc/cloud/cloud.cfg.d \
	  rpmbuild/BUILD/usr/lib/python2.7/site-packages/cloudinit/sources
	docker build -t rpmbuild .
	docker run --rm -it \
		-v $$(pwd)/rpmmacros:/root/.rpmmacros:ro \
		-v $$(pwd)/rpmbuild/:/root/rpmbuild \
		-v $$(pwd)/rpm.spec:/root/rpmbuild/SPECS/rpm.spec:ro \
		-v $$(pwd)/10_vmx_guestinfo.cfg:/root/rpmbuild/BUILD/etc/cloud/cloud.cfg.d/10_vmx_guestinfo.cfg:ro \
		-v $$(pwd)/DataSourceVmxGuestinfo.py:/root/rpmbuild/BUILD/usr/lib/python2.7/site-packages/cloudinit/sources/DataSourceVmxGuestinfo.py:ro \
		rpmbuild \
		rpmbuild -ba /root/rpmbuild/SPECS/rpm.spec
