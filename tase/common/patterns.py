import mimetypes
import re
import string
from io import StringIO
from typing import Optional, Deque

# From https://svn.apache.org/repos/asf/httpd/httpd/trunk/docs/conf/mime.types.
# Extended with extra mime types specific to Telegram.
mime_types = """
# This file maps Internet media types to unique file extension(s).
# Although created for httpd, this file is used by many software systems
# and has been placed in the public domain for unlimited redistribution.
#
# The table below contains both registered and (common) unregistered types.
# A type that has no unique extension can be ignored -- they are listed
# here to guide configurations toward known types and to make it easier to
# identify "new" types.  File extensions are also commonly used to indicate
# content languages and encodings, so choose them carefully.
#
# Internet media types should be registered as described in RFC 4288.
# The registry is at <http://www.iana.org/assignments/media-types/>.
#
# MIME type (lowercased)			Extensions
# ============================================	==========
# application/1d-interleaved-parityfec
# application/3gpdash-qoe-report+xml
# application/3gpp-ims+xml
# application/a2l
# application/activemessage
# application/alto-costmap+json
# application/alto-costmapfilter+json
# application/alto-directory+json
# application/alto-endpointcost+json
# application/alto-endpointcostparams+json
# application/alto-endpointprop+json
# application/alto-endpointpropparams+json
# application/alto-error+json
# application/alto-networkmap+json
# application/alto-networkmapfilter+json
# application/aml
application/andrew-inset			ez
# application/applefile
application/applixware				aw
# application/atf
# application/atfx
application/atom+xml				atom
application/atomcat+xml				atomcat
# application/atomdeleted+xml
# application/atomicmail
application/atomsvc+xml				atomsvc
# application/atxml
# application/auth-policy+xml
# application/bacnet-xdd+zip
# application/batch-smtp
# application/beep+xml
# application/calendar+json
# application/calendar+xml
# application/call-completion
# application/cals-1840
# application/cbor
# application/ccmp+xml
application/ccxml+xml				ccxml
# application/cdfx+xml
application/cdmi-capability			cdmia
application/cdmi-container			cdmic
application/cdmi-domain				cdmid
application/cdmi-object				cdmio
application/cdmi-queue				cdmiq
# application/cdni
# application/cea
# application/cea-2018+xml
# application/cellml+xml
# application/cfw
# application/cms
# application/cnrp+xml
# application/coap-group+json
# application/commonground
# application/conference-info+xml
# application/cpl+xml
# application/csrattrs
# application/csta+xml
# application/cstadata+xml
# application/csvm+json
application/cu-seeme				cu
# application/cybercash
# application/dash+xml
# application/dashdelta
application/davmount+xml			davmount
# application/dca-rft
# application/dcd
# application/dec-dx
# application/dialog-info+xml
# application/dicom
# application/dii
# application/dit
# application/dns
application/docbook+xml				dbk
# application/dskpp+xml
application/dssc+der				dssc
application/dssc+xml				xdssc
# application/dvcs
application/ecmascript				ecma
# application/edi-consent
# application/edi-x12
# application/edifact
# application/efi
# application/emergencycalldata.comment+xml
# application/emergencycalldata.deviceinfo+xml
# application/emergencycalldata.providerinfo+xml
# application/emergencycalldata.serviceinfo+xml
# application/emergencycalldata.subscriberinfo+xml
application/emma+xml				emma
# application/emotionml+xml
# application/encaprtp
# application/epp+xml
application/epub+zip				epub
# application/eshop
# application/example
application/exi					exi
# application/fastinfoset
# application/fastsoap
# application/fdt+xml
# application/fits
application/font-tdpfr				pfr
# application/framework-attributes+xml
# application/geo+json
application/gml+xml				gml
application/gpx+xml				gpx
application/gxf					gxf
# application/gzip
# application/h224
# application/held+xml
# application/http
application/hyperstudio				stk
# application/ibe-key-request+xml
# application/ibe-pkg-reply+xml
# application/ibe-pp-data
# application/iges
# application/im-iscomposing+xml
# application/index
# application/index.cmd
# application/index.obj
# application/index.response
# application/index.vnd
application/inkml+xml				ink inkml
# application/iotp
application/ipfix				ipfix
# application/ipp
# application/isup
# application/its+xml
application/java-archive			jar
application/java-serialized-object		ser
application/java-vm				class
application/javascript				js
# application/jose
# application/jose+json
# application/jrd+json
application/json				json
# application/json-patch+json
# application/json-seq
application/jsonml+json				jsonml
# application/jwk+json
# application/jwk-set+json
# application/jwt
# application/kpml-request+xml
# application/kpml-response+xml
# application/ld+json
# application/lgr+xml
# application/link-format
# application/load-control+xml
application/lost+xml				lostxml
# application/lostsync+xml
# application/lxf
application/mac-binhex40			hqx
application/mac-compactpro			cpt
# application/macwriteii
application/mads+xml				mads
application/marc				mrc
application/marcxml+xml				mrcx
application/mathematica				ma nb mb
application/mathml+xml				mathml
# application/mathml-content+xml
# application/mathml-presentation+xml
# application/mbms-associated-procedure-description+xml
# application/mbms-deregister+xml
# application/mbms-envelope+xml
# application/mbms-msk+xml
# application/mbms-msk-response+xml
# application/mbms-protection-description+xml
# application/mbms-reception-report+xml
# application/mbms-register+xml
# application/mbms-register-response+xml
# application/mbms-schedule+xml
# application/mbms-user-service-description+xml
application/mbox				mbox
# application/media-policy-dataset+xml
# application/media_control+xml
application/mediaservercontrol+xml		mscml
# application/merge-patch+json
application/metalink+xml			metalink
application/metalink4+xml			meta4
application/mets+xml				mets
# application/mf4
# application/mikey
application/mods+xml				mods
# application/moss-keys
# application/moss-signature
# application/mosskey-data
# application/mosskey-request
application/mp21				m21 mp21
application/mp4					mp4s
# application/mpeg4-generic
# application/mpeg4-iod
# application/mpeg4-iod-xmt
# application/mrb-consumer+xml
# application/mrb-publish+xml
# application/msc-ivr+xml
# application/msc-mixer+xml
application/msword				doc dot
application/mxf					mxf
# application/nasdata
# application/news-checkgroups
# application/news-groupinfo
# application/news-transmission
# application/nlsml+xml
# application/nss
# application/ocsp-request
# application/ocsp-response
application/octet-stream	bin dms lrf mar so dist distz pkg bpk dump elc deploy
application/oda					oda
# application/odx
application/oebps-package+xml			opf
application/ogg					ogx
application/omdoc+xml				omdoc
application/onenote				onetoc onetoc2 onetmp onepkg
application/oxps				oxps
# application/p2p-overlay+xml
# application/parityfec
application/patch-ops-error+xml			xer
application/pdf					pdf
# application/pdx
application/pgp-encrypted			pgp
# application/pgp-keys
application/pgp-signature			asc sig
application/pics-rules				prf
# application/pidf+xml
# application/pidf-diff+xml
application/pkcs10				p10
# application/pkcs12
application/pkcs7-mime				p7m p7c
application/pkcs7-signature			p7s
application/pkcs8				p8
application/pkix-attr-cert			ac
application/pkix-cert				cer
application/pkix-crl				crl
application/pkix-pkipath			pkipath
application/pkixcmp				pki
application/pls+xml				pls
# application/poc-settings+xml
application/postscript				ai eps ps
# application/ppsp-tracker+json
# application/problem+json
# application/problem+xml
# application/provenance+xml
# application/prs.alvestrand.titrax-sheet
application/prs.cww				cww
# application/prs.hpub+zip
# application/prs.nprend
# application/prs.plucker
# application/prs.rdf-xml-crypt
# application/prs.xsf+xml
application/pskc+xml				pskcxml
# application/qsig
# application/raptorfec
# application/rdap+json
application/rdf+xml				rdf
application/reginfo+xml				rif
application/relax-ng-compact-syntax		rnc
# application/remote-printing
# application/reputon+json
application/resource-lists+xml			rl
application/resource-lists-diff+xml		rld
# application/rfc+xml
# application/riscos
# application/rlmi+xml
application/rls-services+xml			rs
application/rpki-ghostbusters			gbr
application/rpki-manifest			mft
application/rpki-roa				roa
# application/rpki-updown
application/rsd+xml				rsd
application/rss+xml				rss
application/rtf					rtf
# application/rtploopback
# application/rtx
# application/samlassertion+xml
# application/samlmetadata+xml
application/sbml+xml				sbml
# application/scaip+xml
# application/scim+json
application/scvp-cv-request			scq
application/scvp-cv-response			scs
application/scvp-vp-request			spq
application/scvp-vp-response			spp
application/sdp					sdp
# application/sep+xml
# application/sep-exi
# application/session-info
# application/set-payment
application/set-payment-initiation		setpay
# application/set-registration
application/set-registration-initiation		setreg
# application/sgml
# application/sgml-open-catalog
application/shf+xml				shf
# application/sieve
# application/simple-filter+xml
# application/simple-message-summary
# application/simplesymbolcontainer
# application/slate
# application/smil
application/smil+xml				smi smil
# application/smpte336m
# application/soap+fastinfoset
# application/soap+xml
application/sparql-query			rq
application/sparql-results+xml			srx
# application/spirits-event+xml
# application/sql
application/srgs				gram
application/srgs+xml				grxml
application/sru+xml				sru
application/ssdl+xml				ssdl
application/ssml+xml				ssml
# application/tamp-apex-update
# application/tamp-apex-update-confirm
# application/tamp-community-update
# application/tamp-community-update-confirm
# application/tamp-error
# application/tamp-sequence-adjust
# application/tamp-sequence-adjust-confirm
# application/tamp-status-query
# application/tamp-status-response
# application/tamp-update
# application/tamp-update-confirm
application/tei+xml				tei teicorpus
application/thraud+xml				tfi
# application/timestamp-query
# application/timestamp-reply
application/timestamped-data			tsd
# application/ttml+xml
# application/tve-trigger
# application/ulpfec
# application/urc-grpsheet+xml
# application/urc-ressheet+xml
# application/urc-targetdesc+xml
# application/urc-uisocketdesc+xml
# application/vcard+json
# application/vcard+xml
# application/vemmi
# application/vividence.scriptfile
# application/vnd.3gpp-prose+xml
# application/vnd.3gpp-prose-pc3ch+xml
# application/vnd.3gpp.access-transfer-events+xml
# application/vnd.3gpp.bsf+xml
# application/vnd.3gpp.mid-call+xml
application/vnd.3gpp.pic-bw-large		plb
application/vnd.3gpp.pic-bw-small		psb
application/vnd.3gpp.pic-bw-var			pvb
# application/vnd.3gpp.sms
# application/vnd.3gpp.sms+xml
# application/vnd.3gpp.srvcc-ext+xml
# application/vnd.3gpp.srvcc-info+xml
# application/vnd.3gpp.state-and-event-info+xml
# application/vnd.3gpp.ussd+xml
# application/vnd.3gpp2.bcmcsinfo+xml
# application/vnd.3gpp2.sms
application/vnd.3gpp2.tcap			tcap
# application/vnd.3lightssoftware.imagescal
application/vnd.3m.post-it-notes		pwn
application/vnd.accpac.simply.aso		aso
application/vnd.accpac.simply.imp		imp
application/vnd.acucobol			acu
application/vnd.acucorp				atc acutc
application/vnd.adobe.air-application-installer-package+zip	air
# application/vnd.adobe.flash.movie
application/vnd.adobe.formscentral.fcdt		fcdt
application/vnd.adobe.fxp			fxp fxpl
# application/vnd.adobe.partial-upload
application/vnd.adobe.xdp+xml			xdp
application/vnd.adobe.xfdf			xfdf
# application/vnd.aether.imp
# application/vnd.ah-barcode
application/vnd.ahead.space			ahead
application/vnd.airzip.filesecure.azf		azf
application/vnd.airzip.filesecure.azs		azs
application/vnd.amazon.ebook			azw
# application/vnd.amazon.mobi8-ebook
application/vnd.americandynamics.acc		acc
application/vnd.amiga.ami			ami
# application/vnd.amundsen.maze+xml
application/vnd.android.package-archive		apk
# application/vnd.anki
application/vnd.anser-web-certificate-issue-initiation	cii
application/vnd.anser-web-funds-transfer-initiation	fti
application/vnd.antix.game-component		atx
# application/vnd.apache.thrift.binary
# application/vnd.apache.thrift.compact
# application/vnd.apache.thrift.json
# application/vnd.api+json
application/vnd.apple.installer+xml		mpkg
application/vnd.apple.mpegurl			m3u8
# application/vnd.arastra.swi
application/vnd.aristanetworks.swi		swi
# application/vnd.artsquare
application/vnd.astraea-software.iota		iota
application/vnd.audiograph			aep
# application/vnd.autopackage
# application/vnd.avistar+xml
# application/vnd.balsamiq.bmml+xml
# application/vnd.balsamiq.bmpr
# application/vnd.bekitzur-stech+json
# application/vnd.biopax.rdf+xml
application/vnd.blueice.multipass		mpm
# application/vnd.bluetooth.ep.oob
# application/vnd.bluetooth.le.oob
application/vnd.bmi				bmi
application/vnd.businessobjects			rep
# application/vnd.cab-jscript
# application/vnd.canon-cpdl
# application/vnd.canon-lips
# application/vnd.cendio.thinlinc.clientconf
# application/vnd.century-systems.tcp_stream
application/vnd.chemdraw+xml			cdxml
# application/vnd.chess-pgn
application/vnd.chipnuts.karaoke-mmd		mmd
application/vnd.cinderella			cdy
# application/vnd.cirpack.isdn-ext
# application/vnd.citationstyles.style+xml
application/vnd.claymore			cla
application/vnd.cloanto.rp9			rp9
application/vnd.clonk.c4group			c4g c4d c4f c4p c4u
application/vnd.cluetrust.cartomobile-config		c11amc
application/vnd.cluetrust.cartomobile-config-pkg	c11amz
# application/vnd.coffeescript
# application/vnd.collection+json
# application/vnd.collection.doc+json
# application/vnd.collection.next+json
# application/vnd.comicbook+zip
# application/vnd.commerce-battelle
application/vnd.commonspace			csp
application/vnd.contact.cmsg			cdbcmsg
# application/vnd.coreos.ignition+json
application/vnd.cosmocaller			cmc
application/vnd.crick.clicker			clkx
application/vnd.crick.clicker.keyboard		clkk
application/vnd.crick.clicker.palette		clkp
application/vnd.crick.clicker.template		clkt
application/vnd.crick.clicker.wordbank		clkw
application/vnd.criticaltools.wbs+xml		wbs
application/vnd.ctc-posml			pml
# application/vnd.ctct.ws+xml
# application/vnd.cups-pdf
# application/vnd.cups-postscript
application/vnd.cups-ppd			ppd
# application/vnd.cups-raster
# application/vnd.cups-raw
# application/vnd.curl
application/vnd.curl.car			car
application/vnd.curl.pcurl			pcurl
# application/vnd.cyan.dean.root+xml
# application/vnd.cybank
application/vnd.dart				dart
application/vnd.data-vision.rdz			rdz
# application/vnd.debian.binary-package
application/vnd.dece.data			uvf uvvf uvd uvvd
application/vnd.dece.ttml+xml			uvt uvvt
application/vnd.dece.unspecified		uvx uvvx
application/vnd.dece.zip			uvz uvvz
application/vnd.denovo.fcselayout-link		fe_launch
# application/vnd.desmume.movie
# application/vnd.dir-bi.plate-dl-nosuffix
# application/vnd.dm.delegation+xml
application/vnd.dna				dna
# application/vnd.document+json
application/vnd.dolby.mlp			mlp
# application/vnd.dolby.mobile.1
# application/vnd.dolby.mobile.2
# application/vnd.doremir.scorecloud-binary-document
application/vnd.dpgraph				dpg
application/vnd.dreamfactory			dfac
# application/vnd.drive+json
application/vnd.ds-keypoint			kpxx
# application/vnd.dtg.local
# application/vnd.dtg.local.flash
# application/vnd.dtg.local.html
application/vnd.dvb.ait				ait
# application/vnd.dvb.dvbj
# application/vnd.dvb.esgcontainer
# application/vnd.dvb.ipdcdftnotifaccess
# application/vnd.dvb.ipdcesgaccess
# application/vnd.dvb.ipdcesgaccess2
# application/vnd.dvb.ipdcesgpdd
# application/vnd.dvb.ipdcroaming
# application/vnd.dvb.iptv.alfec-base
# application/vnd.dvb.iptv.alfec-enhancement
# application/vnd.dvb.notif-aggregate-root+xml
# application/vnd.dvb.notif-container+xml
# application/vnd.dvb.notif-generic+xml
# application/vnd.dvb.notif-ia-msglist+xml
# application/vnd.dvb.notif-ia-registration-request+xml
# application/vnd.dvb.notif-ia-registration-response+xml
# application/vnd.dvb.notif-init+xml
# application/vnd.dvb.pfr
application/vnd.dvb.service			svc
# application/vnd.dxr
application/vnd.dynageo				geo
# application/vnd.dzr
# application/vnd.easykaraoke.cdgdownload
# application/vnd.ecdis-update
application/vnd.ecowin.chart			mag
# application/vnd.ecowin.filerequest
# application/vnd.ecowin.fileupdate
# application/vnd.ecowin.series
# application/vnd.ecowin.seriesrequest
# application/vnd.ecowin.seriesupdate
# application/vnd.emclient.accessrequest+xml
application/vnd.enliven				nml
# application/vnd.enphase.envoy
# application/vnd.eprints.data+xml
application/vnd.epson.esf			esf
application/vnd.epson.msf			msf
application/vnd.epson.quickanime		qam
application/vnd.epson.salt			slt
application/vnd.epson.ssf			ssf
# application/vnd.ericsson.quickcall
application/vnd.eszigno3+xml			es3 et3
# application/vnd.etsi.aoc+xml
# application/vnd.etsi.asic-e+zip
# application/vnd.etsi.asic-s+zip
# application/vnd.etsi.cug+xml
# application/vnd.etsi.iptvcommand+xml
# application/vnd.etsi.iptvdiscovery+xml
# application/vnd.etsi.iptvprofile+xml
# application/vnd.etsi.iptvsad-bc+xml
# application/vnd.etsi.iptvsad-cod+xml
# application/vnd.etsi.iptvsad-npvr+xml
# application/vnd.etsi.iptvservice+xml
# application/vnd.etsi.iptvsync+xml
# application/vnd.etsi.iptvueprofile+xml
# application/vnd.etsi.mcid+xml
# application/vnd.etsi.mheg5
# application/vnd.etsi.overload-control-policy-dataset+xml
# application/vnd.etsi.pstn+xml
# application/vnd.etsi.sci+xml
# application/vnd.etsi.simservs+xml
# application/vnd.etsi.timestamp-token
# application/vnd.etsi.tsl+xml
# application/vnd.etsi.tsl.der
# application/vnd.eudora.data
application/vnd.ezpix-album			ez2
application/vnd.ezpix-package			ez3
# application/vnd.f-secure.mobile
# application/vnd.fastcopy-disk-image
application/vnd.fdf				fdf
application/vnd.fdsn.mseed			mseed
application/vnd.fdsn.seed			seed dataless
# application/vnd.ffsns
# application/vnd.filmit.zfc
# application/vnd.fints
# application/vnd.firemonkeys.cloudcell
application/vnd.flographit			gph
application/vnd.fluxtime.clip			ftc
# application/vnd.font-fontforge-sfd
application/vnd.framemaker			fm frame maker book
application/vnd.frogans.fnc			fnc
application/vnd.frogans.ltf			ltf
application/vnd.fsc.weblaunch			fsc
application/vnd.fujitsu.oasys			oas
application/vnd.fujitsu.oasys2			oa2
application/vnd.fujitsu.oasys3			oa3
application/vnd.fujitsu.oasysgp			fg5
application/vnd.fujitsu.oasysprs		bh2
# application/vnd.fujixerox.art-ex
# application/vnd.fujixerox.art4
application/vnd.fujixerox.ddd			ddd
application/vnd.fujixerox.docuworks		xdw
application/vnd.fujixerox.docuworks.binder	xbd
# application/vnd.fujixerox.docuworks.container
# application/vnd.fujixerox.hbpl
# application/vnd.fut-misnet
application/vnd.fuzzysheet			fzs
application/vnd.genomatix.tuxedo		txd
# application/vnd.geo+json
# application/vnd.geocube+xml
application/vnd.geogebra.file			ggb
application/vnd.geogebra.tool			ggt
application/vnd.geometry-explorer		gex gre
application/vnd.geonext				gxt
application/vnd.geoplan				g2w
application/vnd.geospace			g3w
# application/vnd.gerber
# application/vnd.globalplatform.card-content-mgt
# application/vnd.globalplatform.card-content-mgt-response
application/vnd.gmx				gmx
application/vnd.google-earth.kml+xml		kml
application/vnd.google-earth.kmz		kmz
# application/vnd.gov.sk.e-form+xml
# application/vnd.gov.sk.e-form+zip
# application/vnd.gov.sk.xmldatacontainer+xml
application/vnd.grafeq				gqf gqs
# application/vnd.gridmp
application/vnd.groove-account			gac
application/vnd.groove-help			ghf
application/vnd.groove-identity-message		gim
application/vnd.groove-injector			grv
application/vnd.groove-tool-message		gtm
application/vnd.groove-tool-template		tpl
application/vnd.groove-vcard			vcg
# application/vnd.hal+json
application/vnd.hal+xml				hal
application/vnd.handheld-entertainment+xml	zmm
application/vnd.hbci				hbci
# application/vnd.hcl-bireports
# application/vnd.hdt
# application/vnd.heroku+json
application/vnd.hhe.lesson-player		les
application/vnd.hp-hpgl				hpgl
application/vnd.hp-hpid				hpid
application/vnd.hp-hps				hps
application/vnd.hp-jlyt				jlt
application/vnd.hp-pcl				pcl
application/vnd.hp-pclxl			pclxl
# application/vnd.httphone
application/vnd.hydrostatix.sof-data		sfd-hdstx
# application/vnd.hyperdrive+json
# application/vnd.hzn-3d-crossword
# application/vnd.ibm.afplinedata
# application/vnd.ibm.electronic-media
application/vnd.ibm.minipay			mpy
application/vnd.ibm.modcap			afp listafp list3820
application/vnd.ibm.rights-management		irm
application/vnd.ibm.secure-container		sc
application/vnd.iccprofile			icc icm
# application/vnd.ieee.1905
application/vnd.igloader			igl
application/vnd.immervision-ivp			ivp
application/vnd.immervision-ivu			ivu
# application/vnd.ims.imsccv1p1
# application/vnd.ims.imsccv1p2
# application/vnd.ims.imsccv1p3
# application/vnd.ims.lis.v2.result+json
# application/vnd.ims.lti.v2.toolconsumerprofile+json
# application/vnd.ims.lti.v2.toolproxy+json
# application/vnd.ims.lti.v2.toolproxy.id+json
# application/vnd.ims.lti.v2.toolsettings+json
# application/vnd.ims.lti.v2.toolsettings.simple+json
# application/vnd.informedcontrol.rms+xml
# application/vnd.informix-visionary
# application/vnd.infotech.project
# application/vnd.infotech.project+xml
# application/vnd.innopath.wamp.notification
application/vnd.insors.igm			igm
application/vnd.intercon.formnet		xpw xpx
application/vnd.intergeo			i2g
# application/vnd.intertrust.digibox
# application/vnd.intertrust.nncp
application/vnd.intu.qbo			qbo
application/vnd.intu.qfx			qfx
# application/vnd.iptc.g2.catalogitem+xml
# application/vnd.iptc.g2.conceptitem+xml
# application/vnd.iptc.g2.knowledgeitem+xml
# application/vnd.iptc.g2.newsitem+xml
# application/vnd.iptc.g2.newsmessage+xml
# application/vnd.iptc.g2.packageitem+xml
# application/vnd.iptc.g2.planningitem+xml
application/vnd.ipunplugged.rcprofile		rcprofile
application/vnd.irepository.package+xml		irp
application/vnd.is-xpr				xpr
application/vnd.isac.fcs			fcs
application/vnd.jam				jam
# application/vnd.japannet-directory-service
# application/vnd.japannet-jpnstore-wakeup
# application/vnd.japannet-payment-wakeup
# application/vnd.japannet-registration
# application/vnd.japannet-registration-wakeup
# application/vnd.japannet-setstore-wakeup
# application/vnd.japannet-verification
# application/vnd.japannet-verification-wakeup
application/vnd.jcp.javame.midlet-rms		rms
application/vnd.jisp				jisp
application/vnd.joost.joda-archive		joda
# application/vnd.jsk.isdn-ngn
application/vnd.kahootz				ktz ktr
application/vnd.kde.karbon			karbon
application/vnd.kde.kchart			chrt
application/vnd.kde.kformula			kfo
application/vnd.kde.kivio			flw
application/vnd.kde.kontour			kon
application/vnd.kde.kpresenter			kpr kpt
application/vnd.kde.kspread			ksp
application/vnd.kde.kword			kwd kwt
application/vnd.kenameaapp			htke
application/vnd.kidspiration			kia
application/vnd.kinar				kne knp
application/vnd.koan				skp skd skt skm
application/vnd.kodak-descriptor		sse
application/vnd.las.las+xml			lasxml
# application/vnd.liberty-request+xml
application/vnd.llamagraphics.life-balance.desktop	lbd
application/vnd.llamagraphics.life-balance.exchange+xml	lbe
application/vnd.lotus-1-2-3			123
application/vnd.lotus-approach			apr
application/vnd.lotus-freelance			pre
application/vnd.lotus-notes			nsf
application/vnd.lotus-organizer			org
application/vnd.lotus-screencam			scm
application/vnd.lotus-wordpro			lwp
application/vnd.macports.portpkg		portpkg
# application/vnd.mapbox-vector-tile
# application/vnd.marlin.drm.actiontoken+xml
# application/vnd.marlin.drm.conftoken+xml
# application/vnd.marlin.drm.license+xml
# application/vnd.marlin.drm.mdcf
# application/vnd.mason+json
# application/vnd.maxmind.maxmind-db
application/vnd.mcd				mcd
application/vnd.medcalcdata			mc1
application/vnd.mediastation.cdkey		cdkey
# application/vnd.meridian-slingshot
application/vnd.mfer				mwf
application/vnd.mfmp				mfm
# application/vnd.micro+json
application/vnd.micrografx.flo			flo
application/vnd.micrografx.igx			igx
# application/vnd.microsoft.portable-executable
# application/vnd.miele+json
application/vnd.mif				mif
# application/vnd.minisoft-hp3000-save
# application/vnd.mitsubishi.misty-guard.trustweb
application/vnd.mobius.daf			daf
application/vnd.mobius.dis			dis
application/vnd.mobius.mbk			mbk
application/vnd.mobius.mqy			mqy
application/vnd.mobius.msl			msl
application/vnd.mobius.plc			plc
application/vnd.mobius.txf			txf
application/vnd.mophun.application		mpn
application/vnd.mophun.certificate		mpc
# application/vnd.motorola.flexsuite
# application/vnd.motorola.flexsuite.adsi
# application/vnd.motorola.flexsuite.fis
# application/vnd.motorola.flexsuite.gotap
# application/vnd.motorola.flexsuite.kmr
# application/vnd.motorola.flexsuite.ttc
# application/vnd.motorola.flexsuite.wem
# application/vnd.motorola.iprm
application/vnd.mozilla.xul+xml			xul
# application/vnd.ms-3mfdocument
application/vnd.ms-artgalry			cil
# application/vnd.ms-asf
application/vnd.ms-cab-compressed		cab
# application/vnd.ms-color.iccprofile
application/vnd.ms-excel			xls xlm xla xlc xlt xlw
application/vnd.ms-excel.addin.macroenabled.12		xlam
application/vnd.ms-excel.sheet.binary.macroenabled.12	xlsb
application/vnd.ms-excel.sheet.macroenabled.12		xlsm
application/vnd.ms-excel.template.macroenabled.12	xltm
application/vnd.ms-fontobject			eot
application/vnd.ms-htmlhelp			chm
application/vnd.ms-ims				ims
application/vnd.ms-lrm				lrm
# application/vnd.ms-office.activex+xml
application/vnd.ms-officetheme			thmx
# application/vnd.ms-opentype
# application/vnd.ms-package.obfuscated-opentype
application/vnd.ms-pki.seccat			cat
application/vnd.ms-pki.stl			stl
# application/vnd.ms-playready.initiator+xml
application/vnd.ms-powerpoint			ppt pps pot
application/vnd.ms-powerpoint.addin.macroenabled.12		ppam
application/vnd.ms-powerpoint.presentation.macroenabled.12	pptm
application/vnd.ms-powerpoint.slide.macroenabled.12		sldm
application/vnd.ms-powerpoint.slideshow.macroenabled.12		ppsm
application/vnd.ms-powerpoint.template.macroenabled.12		potm
# application/vnd.ms-printdevicecapabilities+xml
# application/vnd.ms-printing.printticket+xml
# application/vnd.ms-printschematicket+xml
application/vnd.ms-project			mpp mpt
# application/vnd.ms-tnef
# application/vnd.ms-windows.devicepairing
# application/vnd.ms-windows.nwprinting.oob
# application/vnd.ms-windows.printerpairing
# application/vnd.ms-windows.wsd.oob
# application/vnd.ms-wmdrm.lic-chlg-req
# application/vnd.ms-wmdrm.lic-resp
# application/vnd.ms-wmdrm.meter-chlg-req
# application/vnd.ms-wmdrm.meter-resp
application/vnd.ms-word.document.macroenabled.12	docm
application/vnd.ms-word.template.macroenabled.12	dotm
application/vnd.ms-works			wps wks wcm wdb
application/vnd.ms-wpl				wpl
application/vnd.ms-xpsdocument			xps
# application/vnd.msa-disk-image
application/vnd.mseq				mseq
# application/vnd.msign
# application/vnd.multiad.creator
# application/vnd.multiad.creator.cif
# application/vnd.music-niff
application/vnd.musician			mus
application/vnd.muvee.style			msty
application/vnd.mynfc				taglet
# application/vnd.ncd.control
# application/vnd.ncd.reference
# application/vnd.nervana
# application/vnd.netfpx
application/vnd.neurolanguage.nlu		nlu
# application/vnd.nintendo.nitro.rom
# application/vnd.nintendo.snes.rom
application/vnd.nitf				ntf nitf
application/vnd.noblenet-directory		nnd
application/vnd.noblenet-sealer			nns
application/vnd.noblenet-web			nnw
# application/vnd.nokia.catalogs
# application/vnd.nokia.conml+wbxml
# application/vnd.nokia.conml+xml
# application/vnd.nokia.iptv.config+xml
# application/vnd.nokia.isds-radio-presets
# application/vnd.nokia.landmark+wbxml
# application/vnd.nokia.landmark+xml
# application/vnd.nokia.landmarkcollection+xml
# application/vnd.nokia.n-gage.ac+xml
application/vnd.nokia.n-gage.data		ngdat
application/vnd.nokia.n-gage.symbian.install	n-gage
# application/vnd.nokia.ncd
# application/vnd.nokia.pcd+wbxml
# application/vnd.nokia.pcd+xml
application/vnd.nokia.radio-preset		rpst
application/vnd.nokia.radio-presets		rpss
application/vnd.novadigm.edm			edm
application/vnd.novadigm.edx			edx
application/vnd.novadigm.ext			ext
# application/vnd.ntt-local.content-share
# application/vnd.ntt-local.file-transfer
# application/vnd.ntt-local.ogw_remote-access
# application/vnd.ntt-local.sip-ta_remote
# application/vnd.ntt-local.sip-ta_tcp_stream
application/vnd.oasis.opendocument.chart		odc
application/vnd.oasis.opendocument.chart-template	otc
application/vnd.oasis.opendocument.database		odb
application/vnd.oasis.opendocument.formula		odf
application/vnd.oasis.opendocument.formula-template	odft
application/vnd.oasis.opendocument.graphics		odg
application/vnd.oasis.opendocument.graphics-template	otg
application/vnd.oasis.opendocument.image		odi
application/vnd.oasis.opendocument.image-template	oti
application/vnd.oasis.opendocument.presentation		odp
application/vnd.oasis.opendocument.presentation-template	otp
application/vnd.oasis.opendocument.spreadsheet		ods
application/vnd.oasis.opendocument.spreadsheet-template	ots
application/vnd.oasis.opendocument.text			odt
application/vnd.oasis.opendocument.text-master		odm
application/vnd.oasis.opendocument.text-template	ott
application/vnd.oasis.opendocument.text-web		oth
# application/vnd.obn
# application/vnd.oftn.l10n+json
# application/vnd.oipf.contentaccessdownload+xml
# application/vnd.oipf.contentaccessstreaming+xml
# application/vnd.oipf.cspg-hexbinary
# application/vnd.oipf.dae.svg+xml
# application/vnd.oipf.dae.xhtml+xml
# application/vnd.oipf.mippvcontrolmessage+xml
# application/vnd.oipf.pae.gem
# application/vnd.oipf.spdiscovery+xml
# application/vnd.oipf.spdlist+xml
# application/vnd.oipf.ueprofile+xml
# application/vnd.oipf.userprofile+xml
application/vnd.olpc-sugar			xo
# application/vnd.oma-scws-config
# application/vnd.oma-scws-http-request
# application/vnd.oma-scws-http-response
# application/vnd.oma.bcast.associated-procedure-parameter+xml
# application/vnd.oma.bcast.drm-trigger+xml
# application/vnd.oma.bcast.imd+xml
# application/vnd.oma.bcast.ltkm
# application/vnd.oma.bcast.notification+xml
# application/vnd.oma.bcast.provisioningtrigger
# application/vnd.oma.bcast.sgboot
# application/vnd.oma.bcast.sgdd+xml
# application/vnd.oma.bcast.sgdu
# application/vnd.oma.bcast.simple-symbol-container
# application/vnd.oma.bcast.smartcard-trigger+xml
# application/vnd.oma.bcast.sprov+xml
# application/vnd.oma.bcast.stkm
# application/vnd.oma.cab-address-book+xml
# application/vnd.oma.cab-feature-handler+xml
# application/vnd.oma.cab-pcc+xml
# application/vnd.oma.cab-subs-invite+xml
# application/vnd.oma.cab-user-prefs+xml
# application/vnd.oma.dcd
# application/vnd.oma.dcdc
application/vnd.oma.dd2+xml			dd2
# application/vnd.oma.drm.risd+xml
# application/vnd.oma.group-usage-list+xml
# application/vnd.oma.lwm2m+json
# application/vnd.oma.lwm2m+tlv
# application/vnd.oma.pal+xml
# application/vnd.oma.poc.detailed-progress-report+xml
# application/vnd.oma.poc.final-report+xml
# application/vnd.oma.poc.groups+xml
# application/vnd.oma.poc.invocation-descriptor+xml
# application/vnd.oma.poc.optimized-progress-report+xml
# application/vnd.oma.push
# application/vnd.oma.scidm.messages+xml
# application/vnd.oma.xcap-directory+xml
# application/vnd.omads-email+xml
# application/vnd.omads-file+xml
# application/vnd.omads-folder+xml
# application/vnd.omaloc-supl-init
# application/vnd.onepager
# application/vnd.openblox.game+xml
# application/vnd.openblox.game-binary
# application/vnd.openeye.oeb
application/vnd.openofficeorg.extension		oxt
# application/vnd.openxmlformats-officedocument.custom-properties+xml
# application/vnd.openxmlformats-officedocument.customxmlproperties+xml
# application/vnd.openxmlformats-officedocument.drawing+xml
# application/vnd.openxmlformats-officedocument.drawingml.chart+xml
# application/vnd.openxmlformats-officedocument.drawingml.chartshapes+xml
# application/vnd.openxmlformats-officedocument.drawingml.diagramcolors+xml
# application/vnd.openxmlformats-officedocument.drawingml.diagramdata+xml
# application/vnd.openxmlformats-officedocument.drawingml.diagramlayout+xml
# application/vnd.openxmlformats-officedocument.drawingml.diagramstyle+xml
# application/vnd.openxmlformats-officedocument.extended-properties+xml
# application/vnd.openxmlformats-officedocument.presentationml.commentauthors+xml
# application/vnd.openxmlformats-officedocument.presentationml.comments+xml
# application/vnd.openxmlformats-officedocument.presentationml.handoutmaster+xml
# application/vnd.openxmlformats-officedocument.presentationml.notesmaster+xml
# application/vnd.openxmlformats-officedocument.presentationml.notesslide+xml
application/vnd.openxmlformats-officedocument.presentationml.presentation	pptx
# application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml
# application/vnd.openxmlformats-officedocument.presentationml.presprops+xml
application/vnd.openxmlformats-officedocument.presentationml.slide	sldx
# application/vnd.openxmlformats-officedocument.presentationml.slide+xml
# application/vnd.openxmlformats-officedocument.presentationml.slidelayout+xml
# application/vnd.openxmlformats-officedocument.presentationml.slidemaster+xml
application/vnd.openxmlformats-officedocument.presentationml.slideshow	ppsx
# application/vnd.openxmlformats-officedocument.presentationml.slideshow.main+xml
# application/vnd.openxmlformats-officedocument.presentationml.slideupdateinfo+xml
# application/vnd.openxmlformats-officedocument.presentationml.tablestyles+xml
# application/vnd.openxmlformats-officedocument.presentationml.tags+xml
application/vnd.openxmlformats-officedocument.presentationml.template	potx
# application/vnd.openxmlformats-officedocument.presentationml.template.main+xml
# application/vnd.openxmlformats-officedocument.presentationml.viewprops+xml
# application/vnd.openxmlformats-officedocument.spreadsheetml.calcchain+xml
# application/vnd.openxmlformats-officedocument.spreadsheetml.chartsheet+xml
# application/vnd.openxmlformats-officedocument.spreadsheetml.comments+xml
# application/vnd.openxmlformats-officedocument.spreadsheetml.connections+xml
# application/vnd.openxmlformats-officedocument.spreadsheetml.dialogsheet+xml
# application/vnd.openxmlformats-officedocument.spreadsheetml.externallink+xml
# application/vnd.openxmlformats-officedocument.spreadsheetml.pivotcachedefinition+xml
# application/vnd.openxmlformats-officedocument.spreadsheetml.pivotcacherecords+xml
# application/vnd.openxmlformats-officedocument.spreadsheetml.pivottable+xml
# application/vnd.openxmlformats-officedocument.spreadsheetml.querytable+xml
# application/vnd.openxmlformats-officedocument.spreadsheetml.revisionheaders+xml
# application/vnd.openxmlformats-officedocument.spreadsheetml.revisionlog+xml
# application/vnd.openxmlformats-officedocument.spreadsheetml.sharedstrings+xml
application/vnd.openxmlformats-officedocument.spreadsheetml.sheet	xlsx
# application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml
# application/vnd.openxmlformats-officedocument.spreadsheetml.sheetmetadata+xml
# application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml
# application/vnd.openxmlformats-officedocument.spreadsheetml.table+xml
# application/vnd.openxmlformats-officedocument.spreadsheetml.tablesinglecells+xml
application/vnd.openxmlformats-officedocument.spreadsheetml.template	xltx
# application/vnd.openxmlformats-officedocument.spreadsheetml.template.main+xml
# application/vnd.openxmlformats-officedocument.spreadsheetml.usernames+xml
# application/vnd.openxmlformats-officedocument.spreadsheetml.volatiledependencies+xml
# application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml
# application/vnd.openxmlformats-officedocument.theme+xml
# application/vnd.openxmlformats-officedocument.themeoverride+xml
# application/vnd.openxmlformats-officedocument.vmldrawing
# application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml
application/vnd.openxmlformats-officedocument.wordprocessingml.document	docx
# application/vnd.openxmlformats-officedocument.wordprocessingml.document.glossary+xml
# application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml
# application/vnd.openxmlformats-officedocument.wordprocessingml.endnotes+xml
# application/vnd.openxmlformats-officedocument.wordprocessingml.fonttable+xml
# application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml
# application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml
# application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml
# application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml
# application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml
application/vnd.openxmlformats-officedocument.wordprocessingml.template	dotx
# application/vnd.openxmlformats-officedocument.wordprocessingml.template.main+xml
# application/vnd.openxmlformats-officedocument.wordprocessingml.websettings+xml
# application/vnd.openxmlformats-package.core-properties+xml
# application/vnd.openxmlformats-package.digital-signature-xmlsignature+xml
# application/vnd.openxmlformats-package.relationships+xml
# application/vnd.oracle.resource+json
# application/vnd.orange.indata
# application/vnd.osa.netdeploy
application/vnd.osgeo.mapguide.package		mgp
# application/vnd.osgi.bundle
application/vnd.osgi.dp				dp
application/vnd.osgi.subsystem			esa
# application/vnd.otps.ct-kip+xml
# application/vnd.oxli.countgraph
# application/vnd.pagerduty+json
application/vnd.palm				pdb pqa oprc
# application/vnd.panoply
# application/vnd.paos.xml
application/vnd.pawaafile			paw
# application/vnd.pcos
application/vnd.pg.format			str
application/vnd.pg.osasli			ei6
# application/vnd.piaccess.application-licence
application/vnd.picsel				efif
application/vnd.pmi.widget			wg
# application/vnd.poc.group-advertisement+xml
application/vnd.pocketlearn			plf
application/vnd.powerbuilder6			pbd
# application/vnd.powerbuilder6-s
# application/vnd.powerbuilder7
# application/vnd.powerbuilder7-s
# application/vnd.powerbuilder75
# application/vnd.powerbuilder75-s
# application/vnd.preminet
application/vnd.previewsystems.box		box
application/vnd.proteus.magazine		mgz
application/vnd.publishare-delta-tree		qps
application/vnd.pvi.ptid1			ptid
# application/vnd.pwg-multiplexed
# application/vnd.pwg-xhtml-print+xml
# application/vnd.qualcomm.brew-app-res
# application/vnd.quarantainenet
application/vnd.quark.quarkxpress		qxd qxt qwd qwt qxl qxb
# application/vnd.quobject-quoxdocument
# application/vnd.radisys.moml+xml
# application/vnd.radisys.msml+xml
# application/vnd.radisys.msml-audit+xml
# application/vnd.radisys.msml-audit-conf+xml
# application/vnd.radisys.msml-audit-conn+xml
# application/vnd.radisys.msml-audit-dialog+xml
# application/vnd.radisys.msml-audit-stream+xml
# application/vnd.radisys.msml-conf+xml
# application/vnd.radisys.msml-dialog+xml
# application/vnd.radisys.msml-dialog-base+xml
# application/vnd.radisys.msml-dialog-fax-detect+xml
# application/vnd.radisys.msml-dialog-fax-sendrecv+xml
# application/vnd.radisys.msml-dialog-group+xml
# application/vnd.radisys.msml-dialog-speech+xml
# application/vnd.radisys.msml-dialog-transform+xml
# application/vnd.rainstor.data
# application/vnd.rapid
# application/vnd.rar
application/vnd.realvnc.bed			bed
application/vnd.recordare.musicxml		mxl
application/vnd.recordare.musicxml+xml		musicxml
# application/vnd.renlearn.rlprint
application/vnd.rig.cryptonote			cryptonote
application/vnd.rim.cod				cod
application/vnd.rn-realmedia			rm
application/vnd.rn-realmedia-vbr		rmvb
application/vnd.route66.link66+xml		link66
# application/vnd.rs-274x
# application/vnd.ruckus.download
# application/vnd.s3sms
application/vnd.sailingtracker.track		st
# application/vnd.sbm.cid
# application/vnd.sbm.mid2
# application/vnd.scribus
# application/vnd.sealed.3df
# application/vnd.sealed.csf
# application/vnd.sealed.doc
# application/vnd.sealed.eml
# application/vnd.sealed.mht
# application/vnd.sealed.net
# application/vnd.sealed.ppt
# application/vnd.sealed.tiff
# application/vnd.sealed.xls
# application/vnd.sealedmedia.softseal.html
# application/vnd.sealedmedia.softseal.pdf
application/vnd.seemail				see
application/vnd.sema				sema
application/vnd.semd				semd
application/vnd.semf				semf
application/vnd.shana.informed.formdata		ifm
application/vnd.shana.informed.formtemplate	itp
application/vnd.shana.informed.interchange	iif
application/vnd.shana.informed.package		ipk
application/vnd.simtech-mindmapper		twd twds
# application/vnd.siren+json
application/vnd.smaf				mmf
# application/vnd.smart.notebook
application/vnd.smart.teacher			teacher
# application/vnd.software602.filler.form+xml
# application/vnd.software602.filler.form-xml-zip
application/vnd.solent.sdkm+xml			sdkm sdkd
application/vnd.spotfire.dxp			dxp
application/vnd.spotfire.sfs			sfs
# application/vnd.sss-cod
# application/vnd.sss-dtf
# application/vnd.sss-ntf
application/vnd.stardivision.calc		sdc
application/vnd.stardivision.draw		sda
application/vnd.stardivision.impress		sdd
application/vnd.stardivision.math		smf
application/vnd.stardivision.writer		sdw vor
application/vnd.stardivision.writer-global	sgl
application/vnd.stepmania.package		smzip
application/vnd.stepmania.stepchart		sm
# application/vnd.street-stream
# application/vnd.sun.wadl+xml
application/vnd.sun.xml.calc			sxc
application/vnd.sun.xml.calc.template		stc
application/vnd.sun.xml.draw			sxd
application/vnd.sun.xml.draw.template		std
application/vnd.sun.xml.impress			sxi
application/vnd.sun.xml.impress.template	sti
application/vnd.sun.xml.math			sxm
application/vnd.sun.xml.writer			sxw
application/vnd.sun.xml.writer.global		sxg
application/vnd.sun.xml.writer.template		stw
application/vnd.sus-calendar			sus susp
application/vnd.svd				svd
# application/vnd.swiftview-ics
application/vnd.symbian.install			sis sisx
application/vnd.syncml+xml			xsm
application/vnd.syncml.dm+wbxml			bdm
application/vnd.syncml.dm+xml			xdm
# application/vnd.syncml.dm.notification
# application/vnd.syncml.dmddf+wbxml
# application/vnd.syncml.dmddf+xml
# application/vnd.syncml.dmtnds+wbxml
# application/vnd.syncml.dmtnds+xml
# application/vnd.syncml.ds.notification
application/vnd.tao.intent-module-archive	tao
application/vnd.tcpdump.pcap			pcap cap dmp
# application/vnd.tmd.mediaflex.api+xml
# application/vnd.tml
application/vnd.tmobile-livetv			tmo
application/vnd.trid.tpt			tpt
application/vnd.triscape.mxs			mxs
application/vnd.trueapp				tra
# application/vnd.truedoc
# application/vnd.ubisoft.webplayer
application/vnd.ufdl				ufd ufdl
application/vnd.uiq.theme			utz
application/vnd.umajin				umj
application/vnd.unity				unityweb
application/vnd.uoml+xml			uoml
# application/vnd.uplanet.alert
# application/vnd.uplanet.alert-wbxml
# application/vnd.uplanet.bearer-choice
# application/vnd.uplanet.bearer-choice-wbxml
# application/vnd.uplanet.cacheop
# application/vnd.uplanet.cacheop-wbxml
# application/vnd.uplanet.channel
# application/vnd.uplanet.channel-wbxml
# application/vnd.uplanet.list
# application/vnd.uplanet.list-wbxml
# application/vnd.uplanet.listcmd
# application/vnd.uplanet.listcmd-wbxml
# application/vnd.uplanet.signal
# application/vnd.uri-map
# application/vnd.valve.source.material
application/vnd.vcx				vcx
# application/vnd.vd-study
# application/vnd.vectorworks
# application/vnd.vel+json
# application/vnd.verimatrix.vcas
# application/vnd.vidsoft.vidconference
application/vnd.visio				vsd vst vss vsw
application/vnd.visionary			vis
# application/vnd.vividence.scriptfile
application/vnd.vsf				vsf
# application/vnd.wap.sic
# application/vnd.wap.slc
application/vnd.wap.wbxml			wbxml
application/vnd.wap.wmlc			wmlc
application/vnd.wap.wmlscriptc			wmlsc
application/vnd.webturbo			wtb
# application/vnd.wfa.p2p
# application/vnd.wfa.wsc
# application/vnd.windows.devicepairing
# application/vnd.wmc
# application/vnd.wmf.bootstrap
# application/vnd.wolfram.mathematica
# application/vnd.wolfram.mathematica.package
application/vnd.wolfram.player			nbp
application/vnd.wordperfect			wpd
application/vnd.wqd				wqd
# application/vnd.wrq-hp3000-labelled
application/vnd.wt.stf				stf
# application/vnd.wv.csp+wbxml
# application/vnd.wv.csp+xml
# application/vnd.wv.ssp+xml
# application/vnd.xacml+json
application/vnd.xara				xar
application/vnd.xfdl				xfdl
# application/vnd.xfdl.webform
# application/vnd.xmi+xml
# application/vnd.xmpie.cpkg
# application/vnd.xmpie.dpkg
# application/vnd.xmpie.plan
# application/vnd.xmpie.ppkg
# application/vnd.xmpie.xlim
application/vnd.yamaha.hv-dic			hvd
application/vnd.yamaha.hv-script		hvs
application/vnd.yamaha.hv-voice			hvp
application/vnd.yamaha.openscoreformat			osf
application/vnd.yamaha.openscoreformat.osfpvg+xml	osfpvg
# application/vnd.yamaha.remote-setup
application/vnd.yamaha.smaf-audio		saf
application/vnd.yamaha.smaf-phrase		spf
# application/vnd.yamaha.through-ngn
# application/vnd.yamaha.tunnel-udpencap
# application/vnd.yaoweme
application/vnd.yellowriver-custom-menu		cmp
application/vnd.zul				zir zirz
application/vnd.zzazz.deck+xml			zaz
application/voicexml+xml			vxml
# application/vq-rtcpxr
# application/watcherinfo+xml
# application/whoispp-query
# application/whoispp-response
application/widget				wgt
application/winhlp				hlp
# application/wita
# application/wordperfect5.1
application/wsdl+xml				wsdl
application/wspolicy+xml			wspolicy
application/x-7z-compressed			7z
application/x-abiword				abw
application/x-ace-compressed			ace
# application/x-amf
application/x-apple-diskimage			dmg
application/x-authorware-bin			aab x32 u32 vox
application/x-authorware-map			aam
application/x-authorware-seg			aas
application/x-bcpio				bcpio
application/x-bittorrent			torrent
application/x-blorb				blb blorb
application/x-bzip				bz
application/x-bzip2				bz2 boz
application/x-cbr				cbr cba cbt cbz cb7
application/x-cdlink				vcd
application/x-cfs-compressed			cfs
application/x-chat				chat
application/x-chess-pgn				pgn
# application/x-compress
application/x-conference			nsc
application/x-cpio				cpio
application/x-csh				csh
application/x-debian-package			deb udeb
application/x-dgc-compressed			dgc
application/x-director			dir dcr dxr cst cct cxt w3d fgd swa
application/x-doom				wad
application/x-dtbncx+xml			ncx
application/x-dtbook+xml			dtb
application/x-dtbresource+xml			res
application/x-dvi				dvi
application/x-envoy				evy
application/x-eva				eva
application/x-font-bdf				bdf
# application/x-font-dos
# application/x-font-framemaker
application/x-font-ghostscript			gsf
# application/x-font-libgrx
application/x-font-linux-psf			psf
application/x-font-pcf				pcf
application/x-font-snf				snf
# application/x-font-speedo
# application/x-font-sunos-news
application/x-font-type1			pfa pfb pfm afm
# application/x-font-vfont
application/x-freearc				arc
application/x-futuresplash			spl
application/x-gca-compressed			gca
application/x-glulx				ulx
application/x-gnumeric				gnumeric
application/x-gramps-xml			gramps
application/x-gtar				gtar
# application/x-gzip
application/x-hdf				hdf
application/x-install-instructions		install
application/x-iso9660-image			iso
application/x-java-jnlp-file			jnlp
application/x-latex				latex
application/x-lzh-compressed			lzh lha
application/x-mie				mie
application/x-mobipocket-ebook			prc mobi
application/x-ms-application			application
application/x-ms-shortcut			lnk
application/x-ms-wmd				wmd
application/x-ms-wmz				wmz
application/x-ms-xbap				xbap
application/x-msaccess				mdb
application/x-msbinder				obd
application/x-mscardfile			crd
application/x-msclip				clp
application/x-msdownload			exe dll com bat msi
application/x-msmediaview			mvb m13 m14
application/x-msmetafile			wmf wmz emf emz
application/x-msmoney				mny
application/x-mspublisher			pub
application/x-msschedule			scd
application/x-msterminal			trm
application/x-mswrite				wri
application/x-netcdf				nc cdf
application/x-nzb				nzb
application/x-pkcs12				p12 pfx
application/x-pkcs7-certificates		p7b spc
application/x-pkcs7-certreqresp			p7r
application/x-rar-compressed			rar
application/x-research-info-systems		ris
application/x-sh				sh
application/x-shar				shar
application/x-shockwave-flash			swf
application/x-silverlight-app			xap
application/x-sql				sql
application/x-stuffit				sit
application/x-stuffitx				sitx
application/x-subrip				srt
application/x-sv4cpio				sv4cpio
application/x-sv4crc				sv4crc
application/x-t3vm-image			t3
application/x-tads				gam
application/x-tar				tar
application/x-tcl				tcl
application/x-tex				tex
application/x-tex-tfm				tfm
application/x-texinfo				texinfo texi
application/x-tgif				obj
application/x-ustar				ustar
application/x-wais-source			src
# application/x-www-form-urlencoded
application/x-x509-ca-cert			der crt
application/x-xfig				fig
application/x-xliff+xml				xlf
application/x-xpinstall				xpi
application/x-xz				xz
application/x-zmachine				z1 z2 z3 z4 z5 z6 z7 z8
# application/x400-bp
# application/xacml+xml
application/xaml+xml				xaml
# application/xcap-att+xml
# application/xcap-caps+xml
application/xcap-diff+xml			xdf
# application/xcap-el+xml
# application/xcap-error+xml
# application/xcap-ns+xml
# application/xcon-conference-info+xml
# application/xcon-conference-info-diff+xml
application/xenc+xml				xenc
application/xhtml+xml				xhtml xht
# application/xhtml-voice+xml
application/xml					xml xsl
application/xml-dtd				dtd
# application/xml-external-parsed-entity
# application/xml-patch+xml
# application/xmpp+xml
application/xop+xml				xop
application/xproc+xml				xpl
application/xslt+xml				xslt
application/xspf+xml				xspf
application/xv+xml				mxml xhvml xvml xvm
application/yang				yang
application/yin+xml				yin
application/zip					zip
# application/zlib
# audio/1d-interleaved-parityfec
# audio/32kadpcm
# audio/3gpp
# audio/3gpp2
# audio/ac3
audio/adpcm					adp
# audio/amr
# audio/amr-wb
# audio/amr-wb+
# audio/aptx
# audio/asc
# audio/atrac-advanced-lossless
# audio/atrac-x
# audio/atrac3
audio/basic					au snd
# audio/bv16
# audio/bv32
# audio/clearmode
# audio/cn
# audio/dat12
# audio/dls
# audio/dsr-es201108
# audio/dsr-es202050
# audio/dsr-es202211
# audio/dsr-es202212
# audio/dv
# audio/dvi4
# audio/eac3
# audio/encaprtp
# audio/evrc
# audio/evrc-qcp
# audio/evrc0
# audio/evrc1
# audio/evrcb
# audio/evrcb0
# audio/evrcb1
# audio/evrcnw
# audio/evrcnw0
# audio/evrcnw1
# audio/evrcwb
# audio/evrcwb0
# audio/evrcwb1
# audio/evs
# audio/example
# audio/fwdred
# audio/g711-0
# audio/g719
# audio/g722
# audio/g7221
# audio/g723
# audio/g726-16
# audio/g726-24
# audio/g726-32
# audio/g726-40
# audio/g728
# audio/g729
# audio/g7291
# audio/g729d
# audio/g729e
# audio/gsm
# audio/gsm-efr
# audio/gsm-hr-08
# audio/ilbc
# audio/ip-mr_v2.5
# audio/isac
# audio/l16
# audio/l20
# audio/l24
# audio/l8
# audio/lpc
audio/midi					mid midi kar rmi
# audio/mobile-xmf
audio/mp4					m4a mp4a
# audio/mp4a-latm
# audio/mpa
# audio/mpa-robust
audio/mpeg					mp3 mpga mp2 mp2a m2a m3a
# audio/mpeg4-generic
# audio/musepack
audio/ogg					ogg oga spx
# audio/opus
# audio/parityfec
# audio/pcma
# audio/pcma-wb
# audio/pcmu
# audio/pcmu-wb
# audio/prs.sid
# audio/qcelp
# audio/raptorfec
# audio/red
# audio/rtp-enc-aescm128
# audio/rtp-midi
# audio/rtploopback
# audio/rtx
audio/s3m					s3m
audio/silk					sil
# audio/smv
# audio/smv-qcp
# audio/smv0
# audio/sp-midi
# audio/speex
# audio/t140c
# audio/t38
# audio/telephone-event
# audio/tone
# audio/uemclip
# audio/ulpfec
# audio/vdvi
# audio/vmr-wb
# audio/vnd.3gpp.iufp
# audio/vnd.4sb
# audio/vnd.audiokoz
# audio/vnd.celp
# audio/vnd.cisco.nse
# audio/vnd.cmles.radio-events
# audio/vnd.cns.anp1
# audio/vnd.cns.inf1
audio/vnd.dece.audio				uva uvva
audio/vnd.digital-winds				eol
# audio/vnd.dlna.adts
# audio/vnd.dolby.heaac.1
# audio/vnd.dolby.heaac.2
# audio/vnd.dolby.mlp
# audio/vnd.dolby.mps
# audio/vnd.dolby.pl2
# audio/vnd.dolby.pl2x
# audio/vnd.dolby.pl2z
# audio/vnd.dolby.pulse.1
audio/vnd.dra					dra
audio/vnd.dts					dts
audio/vnd.dts.hd				dtshd
# audio/vnd.dvb.file
# audio/vnd.everad.plj
# audio/vnd.hns.audio
audio/vnd.lucent.voice				lvp
audio/vnd.ms-playready.media.pya		pya
# audio/vnd.nokia.mobile-xmf
# audio/vnd.nortel.vbk
audio/vnd.nuera.ecelp4800			ecelp4800
audio/vnd.nuera.ecelp7470			ecelp7470
audio/vnd.nuera.ecelp9600			ecelp9600
# audio/vnd.octel.sbc
# audio/vnd.qcelp
# audio/vnd.rhetorex.32kadpcm
audio/vnd.rip					rip
# audio/vnd.sealedmedia.softseal.mpeg
# audio/vnd.vmx.cvsd
# audio/vorbis
# audio/vorbis-config
audio/webm					weba
audio/x-aac					aac
audio/x-aiff					aif aiff aifc
audio/x-caf					caf
audio/x-flac					flac
audio/x-matroska				mka
audio/x-mpegurl					m3u
audio/x-ms-wax					wax
audio/x-ms-wma					wma
audio/x-pn-realaudio				ram ra
audio/x-pn-realaudio-plugin			rmp
# audio/x-tta
audio/x-wav					wav
audio/xm					xm
chemical/x-cdx					cdx
chemical/x-cif					cif
chemical/x-cmdf					cmdf
chemical/x-cml					cml
chemical/x-csml					csml
# chemical/x-pdb
chemical/x-xyz					xyz
font/collection					ttc
font/otf					otf
# font/sfnt
font/ttf					ttf
font/woff					woff
font/woff2					woff2
image/bmp					bmp
image/cgm					cgm
# image/dicom-rle
# image/emf
# image/example
# image/fits
image/g3fax					g3
image/gif					gif
image/ief					ief
# image/jls
# image/jp2
image/jpeg					jpg jpeg jpe
# image/jpm
# image/jpx
image/ktx					ktx
# image/naplps
image/png					png
image/prs.btif					btif
# image/prs.pti
# image/pwg-raster
image/sgi					sgi
image/svg+xml					svg svgz
# image/t38
image/tiff					tiff tif
# image/tiff-fx
image/vnd.adobe.photoshop			psd
# image/vnd.airzip.accelerator.azv
# image/vnd.cns.inf2
image/vnd.dece.graphic				uvi uvvi uvg uvvg
image/vnd.djvu					djvu djv
image/vnd.dvb.subtitle				sub
image/vnd.dwg					dwg
image/vnd.dxf					dxf
image/vnd.fastbidsheet				fbs
image/vnd.fpx					fpx
image/vnd.fst					fst
image/vnd.fujixerox.edmics-mmr			mmr
image/vnd.fujixerox.edmics-rlc			rlc
# image/vnd.globalgraphics.pgb
# image/vnd.microsoft.icon
# image/vnd.mix
# image/vnd.mozilla.apng
image/vnd.ms-modi				mdi
image/vnd.ms-photo				wdp
image/vnd.net-fpx				npx
# image/vnd.radiance
# image/vnd.sealed.png
# image/vnd.sealedmedia.softseal.gif
# image/vnd.sealedmedia.softseal.jpg
# image/vnd.svf
# image/vnd.tencent.tap
# image/vnd.valve.source.texture
image/vnd.wap.wbmp				wbmp
image/vnd.xiff					xif
# image/vnd.zbrush.pcx
image/webp					webp
# image/wmf
image/x-3ds					3ds
image/x-cmu-raster				ras
image/x-cmx					cmx
image/x-freehand				fh fhc fh4 fh5 fh7
image/x-icon					ico
image/x-mrsid-image				sid
image/x-pcx					pcx
image/x-pict					pic pct
image/x-portable-anymap				pnm
image/x-portable-bitmap				pbm
image/x-portable-graymap			pgm
image/x-portable-pixmap				ppm
image/x-rgb					rgb
image/x-tga					tga
image/x-xbitmap					xbm
image/x-xpixmap					xpm
image/x-xwindowdump				xwd
# message/cpim
# message/delivery-status
# message/disposition-notification
# message/example
# message/external-body
# message/feedback-report
# message/global
# message/global-delivery-status
# message/global-disposition-notification
# message/global-headers
# message/http
# message/imdn+xml
# message/news
# message/partial
message/rfc822					eml mime
# message/s-http
# message/sip
# message/sipfrag
# message/tracking-status
# message/vnd.si.simp
# message/vnd.wfa.wsc
# model/example
# model/gltf+json
model/iges					igs iges
model/mesh					msh mesh silo
model/vnd.collada+xml				dae
model/vnd.dwf					dwf
# model/vnd.flatland.3dml
model/vnd.gdl					gdl
# model/vnd.gs-gdl
# model/vnd.gs.gdl
model/vnd.gtw					gtw
# model/vnd.moml+xml
model/vnd.mts					mts
# model/vnd.opengex
# model/vnd.parasolid.transmit.binary
# model/vnd.parasolid.transmit.text
# model/vnd.rosette.annotated-data-model
# model/vnd.valve.source.compiled-map
model/vnd.vtu					vtu
model/vrml					wrl vrml
model/x3d+binary				x3db x3dbz
# model/x3d+fastinfoset
model/x3d+vrml					x3dv x3dvz
model/x3d+xml					x3d x3dz
# model/x3d-vrml
# multipart/alternative
# multipart/appledouble
# multipart/byteranges
# multipart/digest
# multipart/encrypted
# multipart/example
# multipart/form-data
# multipart/header-set
# multipart/mixed
# multipart/parallel
# multipart/related
# multipart/report
# multipart/signed
# multipart/voice-message
# multipart/x-mixed-replace
# text/1d-interleaved-parityfec
text/cache-manifest				appcache
text/calendar					ics ifb
text/css					css
text/csv					csv
# text/csv-schema
# text/directory
# text/dns
# text/ecmascript
# text/encaprtp
# text/enriched
# text/example
# text/fwdred
# text/grammar-ref-list
text/html					html htm
# text/javascript
# text/jcr-cnd
# text/markdown
# text/mizar
text/n3						n3
# text/parameters
# text/parityfec
text/plain					txt text conf def list log in
# text/provenance-notation
# text/prs.fallenstein.rst
text/prs.lines.tag				dsc
# text/prs.prop.logic
# text/raptorfec
# text/red
# text/rfc822-headers
text/richtext					rtx
# text/rtf
# text/rtp-enc-aescm128
# text/rtploopback
# text/rtx
text/sgml					sgml sgm
# text/t140
text/tab-separated-values			tsv
text/troff					t tr roff man me ms
text/turtle					ttl
# text/ulpfec
text/uri-list					uri uris urls
text/vcard					vcard
# text/vnd.a
# text/vnd.abc
text/vnd.curl					curl
text/vnd.curl.dcurl				dcurl
text/vnd.curl.mcurl				mcurl
text/vnd.curl.scurl				scurl
# text/vnd.debian.copyright
# text/vnd.dmclientscript
text/vnd.dvb.subtitle				sub
# text/vnd.esmertec.theme-descriptor
text/vnd.fly					fly
text/vnd.fmi.flexstor				flx
text/vnd.graphviz				gv
text/vnd.in3d.3dml				3dml
text/vnd.in3d.spot				spot
# text/vnd.iptc.newsml
# text/vnd.iptc.nitf
# text/vnd.latex-z
# text/vnd.motorola.reflex
# text/vnd.ms-mediapackage
# text/vnd.net2phone.commcenter.command
# text/vnd.radisys.msml-basic-layout
# text/vnd.si.uricatalogue
text/vnd.sun.j2me.app-descriptor		jad
# text/vnd.trolltech.linguist
# text/vnd.wap.si
# text/vnd.wap.sl
text/vnd.wap.wml				wml
text/vnd.wap.wmlscript				wmls
text/x-asm					s asm
text/x-c					c cc cxx cpp h hh dic
text/x-fortran					f for f77 f90
text/x-java-source				java
text/x-nfo					nfo
text/x-opml					opml
text/x-pascal					p pas
text/x-setext					etx
text/x-sfv					sfv
text/x-uuencode					uu
text/x-vcalendar				vcs
text/x-vcard					vcf
# text/xml
# text/xml-external-parsed-entity
# video/1d-interleaved-parityfec
video/3gpp					3gp
# video/3gpp-tt
video/3gpp2					3g2
# video/bmpeg
# video/bt656
# video/celb
# video/dv
# video/encaprtp
# video/example
video/h261					h261
video/h263					h263
# video/h263-1998
# video/h263-2000
video/h264					h264
# video/h264-rcdo
# video/h264-svc
# video/h265
# video/iso.segment
video/jpeg					jpgv
# video/jpeg2000
video/jpm					jpm jpgm
video/mj2					mj2 mjp2
# video/mp1s
# video/mp2p
# video/mp2t
video/mp4					mp4 mp4v mpg4
# video/mp4v-es
video/mpeg					mpeg mpg mpe m1v m2v
# video/mpeg4-generic
# video/mpv
# video/nv
video/ogg					ogv
# video/parityfec
# video/pointer
video/quicktime					qt mov
# video/raptorfec
# video/raw
# video/rtp-enc-aescm128
# video/rtploopback
# video/rtx
# video/smpte292m
# video/ulpfec
# video/vc1
# video/vnd.cctv
video/vnd.dece.hd				uvh uvvh
video/vnd.dece.mobile				uvm uvvm
# video/vnd.dece.mp4
video/vnd.dece.pd				uvp uvvp
video/vnd.dece.sd				uvs uvvs
video/vnd.dece.video				uvv uvvv
# video/vnd.directv.mpeg
# video/vnd.directv.mpeg-tts
# video/vnd.dlna.mpeg-tts
video/vnd.dvb.file				dvb
video/vnd.fvt					fvt
# video/vnd.hns.video
# video/vnd.iptvforum.1dparityfec-1010
# video/vnd.iptvforum.1dparityfec-2005
# video/vnd.iptvforum.2dparityfec-1010
# video/vnd.iptvforum.2dparityfec-2005
# video/vnd.iptvforum.ttsavc
# video/vnd.iptvforum.ttsmpeg2
# video/vnd.motorola.video
# video/vnd.motorola.videop
video/vnd.mpegurl				mxu m4u
video/vnd.ms-playready.media.pyv		pyv
# video/vnd.nokia.interleaved-multimedia
# video/vnd.nokia.videovoip
# video/vnd.objectvideo
# video/vnd.radgamettools.bink
# video/vnd.radgamettools.smacker
# video/vnd.sealed.mpeg1
# video/vnd.sealed.mpeg4
# video/vnd.sealed.swf
# video/vnd.sealedmedia.softseal.mov
video/vnd.uvvu.mp4				uvu uvvu
video/vnd.vivo					viv
# video/vp8
video/webm					webm
video/x-f4v					f4v
video/x-fli					fli
video/x-flv					flv
video/x-m4v					m4v
video/x-matroska				mkv mk3d mks
video/x-mng					mng
video/x-ms-asf					asf asx
video/x-ms-vob					vob
video/x-ms-wm					wm
video/x-ms-wmv					wmv
video/x-ms-wmx					wmx
video/x-ms-wvx					wvx
video/x-msvideo					avi
video/x-sgi-movie				movie
video/x-smv					smv
x-conference/x-cooltalk				ice

# Telegram animated stickers
application/x-bad-tgsticker		tgs
application/x-tgsticker		tgs
"""

mimetypes = mimetypes.MimeTypes()
mimetypes.readfp(StringIO(mime_types))

telegram_username_pattern = re.compile(
    r"(?:@|(?:(?:(?:https?://)?t(?:elegram)?)\.me\/))(?P<username>[a-zA-Z0-9_]{5,32})",
    re.IGNORECASE,
)
url_with_protocol_pattern = re.compile(
    "[a-zA-Z]+:\\/\\/(?:www\\.)?[-a-zA-Z0-9@:%._\\+~#=]{1,256}\\.[a-zA-Z0-9()]{1,6}\\b(?:[-a-zA-Z0-9()@:%_\\+.~#?&\\/=]*)"
)

url_pattern = re.compile(
    "[-a-zA-Z0-9@:%._\\+~#=]{1,256}\\.[a-zA-Z0-9()]{1,6}\\b(?:[-a-zA-Z0-9()@:%_\\+.~#?&\\/=]*)"
)

punctuation_pattern = re.compile(r"[" + string.punctuation + "]")


def guess_mime_type(filename: str) -> Optional[str]:
    return mimetypes.guess_type(filename)[0]


def guess_extension(mime_type: str) -> Optional[str]:
    return mimetypes.guess_extension(mime_type)


def guess_file_name(file_name: str) -> Optional[str]:
    """
    Guess the file name by filtering out extension part

    Parameters
    ----------
    file_name : str
        Raw file name string

    Returns
    -------
    str, optional
        File name without the extension part

    """
    if file_name is None:
        return None

    mime_type = guess_mime_type(file_name)
    if mime_type is None:
        return file_name

    if not mime_type.startswith("audio/"):
        return file_name

    ext = guess_extension(mime_type)
    if ext is None:
        return file_name

    temp = file_name[: file_name.lower().find(ext)]
    if not len(temp):
        return None
    return temp


def remove_usernames(
    text: str,
    extra_strings_to_remove: Deque[str] = None,
) -> Optional[str]:
    """
    Remove usernames and `extra_string_to_remove` parameter from the given `text`

    Parameters
    ----------
    text : str
        Text string to remove the usernames from
    extra_strings_to_remove : deque, default : None
        Extra strings to remove from the `text` parameter

    Returns
    -------
    str, optional
        Modified text after removing usernames if successful, otherwise, return None

    """
    if text is None:
        return None

    text = telegram_username_pattern.sub("", text)
    if extra_strings_to_remove is not None and len(extra_strings_to_remove):
        for to_remove in extra_strings_to_remove:
            if to_remove is None:
                continue
            text = re.sub(f"@{to_remove}", "", text, flags=re.IGNORECASE)

    if not len(text):
        return None

    return text


def remove_urls(
    text: str,
) -> Optional[str]:
    """
    Remove URLs from the given `text`

    Parameters
    ----------
    text : str
        Text string to remove the URLs from

    Returns
    -------
    str, optional
        Modified text after removing URLs if successful, otherwise, return None

    """
    if text is None:
        return None

    text = url_with_protocol_pattern.sub("", text)
    text = url_pattern.sub("", text)

    if not len(text):
        return None

    return text


def remove_punctuations(text: str) -> Optional[str]:
    """
    Remove punctuations from the text

    Parameters
    ----------
    text : str
        Text string to process

    Returns
    -------
    str, optional
        Text without punctuations if successful, otherwise, return None

    """
    if text is None:
        return None
    return punctuation_pattern.sub(" ", text).replace("  ", " ")
