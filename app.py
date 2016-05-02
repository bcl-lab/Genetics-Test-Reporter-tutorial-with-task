from flask import Flask
from auth import *

# we use this to shorten a long resource reference when displaying it
MAX_LINK_LEN = 20
# we only care about genomic stuff here


app = Flask(__name__)


def api_call(api_endpoint):
    '''
    helper function that makes API call 
    '''
    access_token = request.cookies['access_token']
    auth_header = {'Accept': 'application/json', 'Authorization': 'Bearer %s' % access_token}
    resp = requests.get('%s%s' % (API_BASE, api_endpoint), headers=auth_header)
    return resp.json()


@app.route('/')
@require_oauth
def index():
    return redirect('/reports/286e9bab-ffee-41ab-b53b-f219b7d31dec')


# if the user authorize the app, use code to exchange access_token to the server
@app.route('/recv_redirect')
def recv_code():
    code = request.args['code']
    access_token = get_access_token(code)
    resp = redirect('/')
    resp.set_cookie('access_token', access_token)
    return resp


@app.route('/reports/<path:id>')
def report_generate(id):
    '''
    fetch the instances of observationforgenetics profile, reportforgenetics profile, sequence resource of selected
    patient. Then select representative genetics info from these instances.
    '''
    # initiation
    source, gene, variation, coordinate, frequency, condition = [], [], [], [], [], []
    variation_id, seq_reference = None, None
    # read the patient instance by id
    patient = api_call('/Patient/'+id+'?_format=json')
    # search all the observationforgenetics instance for this patient
    observations = api_call('/observationforgenetics?subject:Patient._id='+id+'&_format=json')
    total = observations.get('total')

    for observation in observations['entry']:
        obs_extensions = observation['resource'].get('extension')
        for i in obs_extensions:
            if 'Gene' in i['url']:
                gene = i['valueCodeableConcept'].get('text')
            elif 'Sequence' in i['url']:
                seq_reference = i['valueReference']['reference']
            elif 'VariationId' in i['url']:
                variation_id = i['valueCodeableConcept'].get('coding')[0].get('code')

    sequence = api_call('/'+seq_reference+'?_format=json')
    variation = "%s (observed allele/reference allele is %s/%s)" % (variation_id,
                                                                    sequence['variation']['observedAllele'],
                                                                    sequence['variation']['referenceAllele'])
    coordinate = "%s: chrom %s (%s ~ %s)" % (sequence['referenceSeq'][0]['genomeBuild'].get('text'),
                                             sequence['referenceSeq'][0]['chromosome'].get('text'),
                                             sequence['variation']['start'],
                                             sequence['variation']['end'])

    patient_info = {'name': patient['name'][0]['text'],
                    'gender': patient['gender'][0].upper()+patient['gender'][1:],
                    'id': patient['id']}

    # search for all observationforgenetics instances containing this variant
    observations_for_this_variation = api_call('/observationforgenetics?DNAVariationID='+variation_id+'&_format=json').get('entry')
    subject_id = []
    # collect all patient having this variant
    for entry in observations_for_this_variation:
        id = entry['resource'].get('subject')
        if id and id not in subject_id:
            subject_id.append(id)
    # calculate frequency
    patient_count = api_call('/Patient?_format=json').get('total')
    frequency = float(len(subject_id))/patient_count


    s1 = '''<h2>Genetics Report for %s</h2>
            <p>%s, Patient Id: %s</p>
            <h3>Genetics Information</h3>
            <h4>Variation 1</h4>
            <p>Gene: %s</p>
            <p>Variation: %s</p>
            <p>Coordinate: %s</p>
            <p>Frequency: %f</p>
    ''' % (patient_info['name'], patient_info['gender'], patient_info['id'], gene, variation, coordinate, frequency)

    return s1


if __name__ == '__main__':
    app.run(debug=True, port=8000)
