all: build

rpm-centos7:
	@mkdir -p rpmbuild/centos7/RPMS rpmbuild/centos7/SPECS \
	  rpmbuild/centos7/SRPMS \
	  rpmbuild/centos7/BUILD/etc/cloud/cloud.cfg.d \
	  rpmbuild/centos7/BUILD/usr/lib/python2.7/site-packages/cloudinit/sources
	docker build -f Dockerfile.rpmbuild -t rpmbuild:centos7 .
	docker run --rm -it \
		-v $$(pwd)/rpmmacros:/root/.rpmmacros:ro \
		-v $$(pwd)/rpmbuild/centos7:/root/rpmbuild \
		-v $$(pwd)/rpm.centos7.spec:/root/rpmbuild/SPECS/rpm.spec:ro \
		-v $$(pwd)/99_vmx_guestinfo.cfg:/root/rpmbuild/BUILD/etc/cloud/cloud.cfg.d/99_vmx_guestinfo.cfg:ro \
		-v $$(pwd)/DataSourceVmxGuestinfo.py:/root/rpmbuild/BUILD/usr/lib/python2.7/site-packages/cloudinit/sources/DataSourceVmxGuestinfo.py:ro \
		rpmbuild:centos7 \
		rpmbuild -ba /root/rpmbuild/SPECS/rpm.spec

rpm: rpm-centos7

build: rpm

