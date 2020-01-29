"""Parse sample info files for RNA Cases """


def parse_sampleinfo_rna(data: dict) -> dict:
    """Parse MIP sample info file (RNA).

    Args:
        data (dict): raw YAML input from MIP qc sample info file (RNA)

    Returns:
        dict: parsed data
    """
    case = data['case']
    qcmetrics_parse = data['recipe']['qccollect_ar']

    outdata = {
        'bcftools_merge': data['recipe']['bcftools_merge']['path'],
        'dea_path': data['recipe']['blobfish']['path'],
        'case': case,
        'config_file_path': data['config_file_analysis'],
        'date': data['analysis_date'],
        'is_finished': data['analysisrunstatus'] == 'finished',
        'multiqc_html': data['recipe']['multiqc'][f'{case}_html']['path'],
        'multiqc_json': data['recipe']['multiqc'][f'{case}_json']['path'],
        'pedigree_path': data['pedigree_minimal'],
        'qcmetrics_path': qcmetrics_parse if not isinstance(qcmetrics_parse, dict) else None,
        'samples': [],
        'vep_path': data['recipe']['varianteffectpredictor']['path'],
        'version': data['mip_version'],
        'version_collect_ar_path': data['recipe']['version_collect_ar']['path'],
    }

    for sample_id, sample_data in data['sample'].items():

        sample = {
            'arriba': get_multiple_paths(sample_data, 'arriba_ar'),
            'arriba_report': get_tag_paths(sample_data['recipe']['arriba_ar'], 'report', []),
            'bootstrap_vcf': get_multiple_paths(sample_data, 'bootstrapann'),
            'gatk_asereadcounter': get_multiple_paths(sample_data, 'gatk_asereadcounter'),
            'gffcompare_ar': get_multiple_paths(sample_data, 'gffcompare_ar'),
            'id': sample_id,
            'mark_duplicates': get_multiple_paths(sample_data, 'markduplicates'),
            'salmon_quant': get_multiple_paths(sample_data, 'salmon_quant'),
            'star_fusion': sample_data['recipe']['star_fusion']['path'],
            'stringtie_ar': get_multiple_paths(sample_data, 'stringtie_ar'),
        }

        outdata['samples'].append(sample)

    return outdata


def get_multiple_paths(sample_data: dict, path_key: str) -> list:
    """Get all paths to files of a given type. Use this method if the exact filename is not
    known beforehand.
    Args:
        sample_data (dict): YAML file containing qc sample info
        path_key (str)    : Type of file paths to retrieve

    Returns:
        list: paths to all files of given type
    """
    paths = [file_data['path'] for file_data in sample_data['recipe'][path_key].values()]
    return paths


def get_tag_paths(recipe_data: dict, tag: str, paths: list) -> list:
    """Get all paths to files with a given tag. Use this method if the exact filename is not
    known beforehand and you only want files with a given tag.
    Args:
        recipe_data (dict): Recipe files
        tag (str)         : Type of file paths to retrieve
        paths (list)      : List to store paths in

    Returns:
        list: paths to all files with a specified recipe tag
    """
    for key in recipe_data:
        if key == tag:
            paths.append(recipe_data[key]['path'])
        elif isinstance(recipe_data[key], dict):
            paths = get_tag_paths(recipe_data[key], tag, paths)
    return paths
