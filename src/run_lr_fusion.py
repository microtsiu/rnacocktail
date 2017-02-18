import os
from external_cmd import TimedExternalCmd
from defaults import *
from utils import *
import csv

FORMAT = '%(levelname)s %(asctime)-15s %(name)-20s %(message)s'
logging.basicConfig(level=logging.INFO, format=FORMAT)
logger = logging.getLogger(__name__)



def sort_gpd(in_file,out_file,order_chrs=dict([("%s"%k,k) for k in range(1,23)]+[("MT",23),("X",24),("Y",25)])):
    with open(in_file) as csv_file:
        spamreader = csv.reader(csv_file, delimiter='\t', quotechar='|')
        rows=[]
        for row in spamreader:
            rows.append(row)
        sorted_rows=sorted(rows,key=lambda x: (order_chrs[x[2]],int(x[4])))
        with open(out_file, 'wb') as csvfile:
            spamwriter = csv.writer(csvfile, delimiter='\t',
                                    quotechar='|', quoting=csv.QUOTE_MINIMAL)
            spamwriter.writerows(sorted_rows)


def run_idpfusion(alignment="", short_junction="", long_alignment="",mode_number=0, 
                    short_fasta="", long_fasta="", 
                  ref_genome="", ref_all_gpd="", ref_gpd="", uniqueness_bedgraph="",
                  genome_bowtie2_idx="", transcriptome_bowtie2_idx="",
                  read_length=100,
                  idpfusion_cfg="", idpfusion=IDPFUSION, samtools=SAMTOOLS, 
                  star_dir=STAR_DIR, bowtie2_dir=BOWTIE2_DIR,
                  start=0, sample= "", nthreads=1,
                  workdir=None, outdir=None, timeout=TIMEOUT):

    logger.info("Running long read fusion Detection (IDP-fusion) for %s"%sample)
    if not os.path.exists(alignment):
        logger.error("Aborting!")
        raise Exception("No input short read alignment BAM/SAM file %s"%alignment)
    if not os.path.exists(short_junction):
        logger.error("Aborting!")
        raise Exception("No input short read junction BED file %s"%short_junction)
    if not os.path.exists(long_alignment):
        logger.error("Aborting!")
        raise Exception("No input long read alignment PSL file %s"%long_alignment)
        
    if idpfusion_cfg:
        if not os.path.exists(idpfusion_cfg):
            logger.error("Aborting!")
            raise Exception("No input .cfg file %s"%idpfusion_cfg)
        

    
    if mode_number>0:
        start=4
    
    work_idpfusion="%s/idpfusion/%s/"%(workdir,sample)
    create_dirs([work_idpfusion])

    step=0
    if start<=step:
        logger.info("--------------------------STEP %s--------------------------"%step)
        msg = "Erase IDP-fusion work directory for %s"%sample
        command="rm -rf %s/*" % (
            work_idpfusion)
        command="bash -c \"%s\""%command        
        cmd = TimedExternalCmd(command, logger, raise_exception=False)
        retcode = cmd.run(msg=msg,timeout=timeout)
    step+=1



    idpfusion_log = os.path.join(work_idpfusion, "idpfusion.log")
    idpfusion_log_fd = open(idpfusion_log, "w")

    msg = "converting BAM to SAM for %s"%sample
    logger.info("--------------------------STEP %s--------------------------"%step)
    if start<=step:
        if alignment.endswith('.bam'):
            command = "%s view -h -o %s/alignments.sam %s " % (samtools,work_idpfusion,alignment)
            command="bash -c \"%s\""%command       
            cmd = TimedExternalCmd(command, logger, raise_exception=True)
            retcode = cmd.run(cmd_log_fd_out=idpfusion_log_fd, cmd_log=idpfusion_log, msg=msg, timeout=timeout)
            alignment =  "%s/alignments.sam"%(work_idpfusion)
    else:
        logger.info("Skipping step %d: %s"%(step,msg))
    step+=1


    msg = "Preparing run.cfg for %s"%sample
    if start<=step:
        logger.info("--------------------------STEP %s--------------------------"%step)
        if idpfusion_cfg:
            msg = "copy IDP-fusion .cfg file for %s"%sample
            command="cp  %s %s/run.cfg" % (
                idpfusion_cfg, work_idpfusion)
            command="bash -c \"%s\""%command
            cmd = TimedExternalCmd(command, logger, raise_exception=True)
            retcode = cmd.run(cmd_log_fd_out=idpfusion_log_fd, cmd_log=idpfusion_log, msg=msg, timeout=timeout)   
        else:
            f=open("%s/run.cfg"%work_idpfusion, 'w')
            f.close()

        cgf_dict={}
        with open("%s/run.cfg"%work_idpfusion , 'r') as cfg_file:
            for line in cfg_file:
                line = line.strip()
                if line=='':
                    continue
                if "=" in line and not line[0]=='#' :
                    k,v=line.split("=")
                    k=k.strip()
                    v=v.strip()
                    cgf_dict[k]=v
                    

        with open("%s/run.cfg"%work_idpfusion , 'w') as cfg_file:
            for k,v in cgf_dict.iteritems():
                cfg_file.write("%s = %s \n"%(k,v))
            if "temp_foldername" not in cgf_dict:
                cfg_file.write("temp_foldername = %s/tmp/ \n"%work_idpfusion)
            if "output_foldername" not in cgf_dict:
                cfg_file.write("output_foldername = %s/out/ \n"%work_idpfusion)
            if "Nthread" not in cgf_dict:
                cfg_file.write("Nthread = %d \n"%nthreads)
            if "LR_psl_pathfilename" not in cgf_dict:
                cfg_file.write("LR_psl_pathfilename = %s \n"%long_alignment)
            if "LR_pathfilename" not in cgf_dict:
                cfg_file.write("LR_pathfilename = %s \n"%long_fasta)
            if "SR_sam_pathfilename" not in cgf_dict:
                cfg_file.write("SR_sam_pathfilename = %s \n"%alignment)
            if "SR_jun_pathfilename" not in cgf_dict:
                cfg_file.write("SR_jun_pathfilename = %s \n"%short_junction)
            if "SR_pathfilename" not in cgf_dict:
                cfg_file.write("SR_pathfilename = %s \n"%short_fasta)
            if "SR_aligner_choice" not in cgf_dict:
                cfg_file.write("SR_aligner_choice = STAR \n")
            if "star_path" not in cgf_dict:       
                cfg_file.write("star_path = %s \n"%star_dir)
            if "genome_bowtie2_index_pathfilename" not in cgf_dict:       
                cfg_file.write("genome_bowtie2_index_pathfilename = %s \n"%genome_bowtie2_idx)
            if "transcriptome_bowtie2_index_pathfilename" not in cgf_dict:       
                cfg_file.write("transcriptome_bowtie2_index_pathfilename = %s \n"%transcriptome_bowtie2_idx)
            if "allref_annotation_pathfilename" not in cgf_dict:       
                cfg_file.write("allref_annotation_pathfilename = %s \n"%ref_all_gpd)
            if "ref_annotation_pathfilename" not in cgf_dict:       
                cfg_file.write("ref_annotation_pathfilename = %s \n"%ref_gpd)
            if "genome_pathfilename" not in cgf_dict:       
                cfg_file.write("genome_pathfilename = %s \n"%ref_genome)
            if "estimator_choice" not in cgf_dict:       
                cfg_file.write("estimator_choice = MAP \n")
            if "FPR" not in cgf_dict:       
                cfg_file.write("FPR = 0.05 \n")
            if "Njun_limit" not in cgf_dict:       
                cfg_file.write("Njun_limit = 10 \n")
            if "Niso_limit" not in cgf_dict:       
                cfg_file.write("Niso_limit = 20 \n")
            if "L_exon_limit" not in cgf_dict:       
                cfg_file.write("L_exon_limit = 1700 \n")
            if "L_min_intron" not in cgf_dict:       
                cfg_file.write("L_min_intron = 68 \n")
            if "Bfile_Npt" not in cgf_dict:       
                cfg_file.write("Bfile_Npt = 500 \n")
            if "Bfile_Nbin" not in cgf_dict:       
                cfg_file.write("Bfile_Nbin = 5 \n")
            if "min_LR_overlap_len" not in cgf_dict:       
                cfg_file.write("min_LR_overlap_len = 100 \n")
            if "LR_fusion_point_err_margin" not in cgf_dict:       
                cfg_file.write("LR_fusion_point_err_margin = 20 \n")
            if "min_LR_fusion_point_search_distance" not in cgf_dict:       
                cfg_file.write("min_LR_fusion_point_search_distance = 20 \n")
            if "uniq_LR_alignment_margin_perc" not in cgf_dict:       
                cfg_file.write("uniq_LR_alignment_margin_perc = 20 \n")
            if "Niso_fusion_limit" not in cgf_dict:       
                cfg_file.write("Niso_fusion_limit = 20 \n")
            if "psl_type" not in cgf_dict:       
                cfg_file.write("psl_type = 0 \n")
            if "read_length" not in cgf_dict:       
                cfg_file.write("read_length = %d \n"%read_length)
            if "min_junction_overlap_len" not in cgf_dict:       
                cfg_file.write("min_junction_overlap_len = 10 \n")
            if "I_refjun_isoformconstruction" not in cgf_dict:       
                cfg_file.write("I_refjun_isoformconstruction = 1 \n")
            if "I_ref5end_isoformconstruction" not in cgf_dict:       
                cfg_file.write("I_ref5end_isoformconstruction = 1 \n")
            if "I_ref3end_isoformconstruction" not in cgf_dict:       
                cfg_file.write("I_ref3end_isoformconstruction = 1 \n")
            if "fusion_mode" not in cgf_dict:       
                cfg_file.write("fusion_mode = 1 \n")
            if "uniqueness_bedGraph_pathfilename" not in cgf_dict:       
                cfg_file.write("uniqueness_bedGraph_pathfilename = %s \n"%uniqueness_bedgraph)
            if "exon_construction_junction_span" not in cgf_dict:       
                cfg_file.write("exon_construction_junction_span = 1 \n")
            if "aligner_choice" not in cgf_dict:       
                cfg_file.write("aligner_choice = gmap \n")
    else:
        logger.info("Skipping step %d: %s"%(step,msg))
    step+=1

    if star_dir:
        os.environ["PATH"] += ":%s/"%star_dir
    if bowtie2_dir:
        os.environ["PATH"] += ":%s/"%bowtie2_dir

    
    msg = "IDP-fusion for %s"%sample
    if start<=step:
        logger.info("--------------------------STEP %s--------------------------"%step)
        command="%s %s/run.cfg %d" % (
            idpfusion, work_idpfusion, mode_number)
        command="bash -c \"%s\""%command
        cmd = TimedExternalCmd(command, logger, raise_exception=True)
        retcode = cmd.run(cmd_log_fd_out=idpfusion_log_fd, cmd_log=idpfusion_log, msg=msg, timeout=timeout)   
    else:
        logger.info("Skipping step %d: %s"%(step,msg))
    step+=1
    
    msg = "Convert transcript GPD file to GTF for %s"%sample
    if start<=step:
        logger.info("--------------------------STEP %s--------------------------"%step)
        if os.path.exists("%s/out/isoform.gpd"%work_idpfusion):
            sort_gpd("%s/out/isoform.gpd"%work_idpfusion,"%s/out/isoform_sorted.gpd"%work_idpfusion)
            command="gpd2gtf.py \
                  %s/out/isoform_sorted.gpd %s/out/isoform.exp %s/out/isoform.gtf IDP"%(work_idpfusion,work_idpfusion,work_idpfusion)
            command="bash -c \"%s\""%command
            cmd = TimedExternalCmd(command, logger, raise_exception=True)
            retcode = cmd.run(cmd_log_fd_out=idpfusion_log_fd, cmd_log=idpfusion_log, msg=msg, timeout=timeout)   
    else:
        logger.info("Skipping step %d: %s"%(step,msg))
    step+=1

    out_idpfusion=os.path.join(outdir,"idpfusion",sample)
    create_dirs([out_idpfusion])
    msg="Copy predictions to output directory for %s."%sample
    if start<=step:
        logger.info("--------------------------STEP %s--------------------------"%step)
        if os.path.exists("%s/out/isoform.gtf"%work_idpfusion) and \
           os.path.exists("%s/out/isoform.exp"%work_idpfusion):
            command = "cp %s/out/isoform.gtf %s/isoform.gtf"%(
                       work_idpfusion, out_idpfusion)
            cmd = TimedExternalCmd(command, logger, raise_exception=True)
            retcode = cmd.run(cmd_log_fd_out=idpfusion_log_fd, cmd_log=idpfusion_log, msg=msg, timeout=timeout)   
            
            command = "cp %s/out/isoform.exp %s/isoform.exp"%(
                       work_idpfusion, out_idpfusion)
            cmd = TimedExternalCmd(command, logger, raise_exception=True)
            retcode = cmd.run(cmd_log_fd_out=idpfusion_log_fd, cmd_log=idpfusion_log, msg=msg, timeout=timeout)   
    else:
        logger.info("Skipping step %d: %s"%(step,msg))
    step+=1



    transcripts = ""
    abundances = ""
    if os.path.exists("%s/isoform.gtf"%out_idpfusion) and \
       os.path.exists("%s/isoform.exp"%out_idpfusion):
        logger.info("IDP-fusion was successfull!")
        logger.info("Output isoforms: %s/isoform.gtf"%out_idpfusion)
        logger.info("Output expressions: %s/isoform.exp"%out_idpfusion)
        transcripts = "%s/isoform.gtf"%out_idpfusion   
        abundances = "%s/isoform.exp"%out_idpfusion   
    else:            
        logger.info("IDP-fusion was not successfull!")
    return transcripts,abundances

def run_lr_fusion(long_fusion_caller="IDP-fusion", alignment="",
                  short_junction="", long_alignment="", mode_number=0,
                    short_fasta="", long_fasta="", 
                  ref_genome="", ref_all_gpd="", ref_gpd="", uniqueness_bedgraph="",
                  genome_bowtie2_idx="", transcriptome_bowtie2_idx="",
                  read_length=100,
                  idpfusion_cfg="", idpfusion=IDPFUSION, samtools=SAMTOOLS, 
                  star_dir=STAR_DIR, bowtie2_dir=BOWTIE2_DIR,
                  start=0, sample= "", nthreads=1, 
                  workdir=None, outdir=None, timeout=TIMEOUT):
    transcripts = ""
    abundances = ""
    if long_fusion_caller.upper()=="IDP-FUSION":
        transcripts,abundances=run_idpfusion(alignment=alignment, 
                      short_junction=short_junction, long_alignment=long_alignment, 
                      mode_number=mode_number,
                      short_fasta=short_fasta, long_fasta=long_fasta, 
                      ref_genome=ref_genome, ref_all_gpd=ref_all_gpd, 
                      ref_gpd=ref_gpd, uniqueness_bedgraph=uniqueness_bedgraph,
                      genome_bowtie2_idx=genome_bowtie2_idx, transcriptome_bowtie2_idx=transcriptome_bowtie2_idx,
                      read_length=read_length,
                      idpfusion_cfg=idpfusion_cfg, idpfusion=idpfusion, samtools=samtools, 
                      star_dir=star_dir,
                      bowtie2_dir=bowtie2_dir,
                      start=start, sample= sample, nthreads=nthreads,
                      workdir=workdir, outdir=outdir, timeout=timeout)
    return transcripts,abundances