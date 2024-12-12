import streamlit as st
import pandas as pd
import requests
import json
from bs4 import BeautifulSoup
import logging
logging.basicConfig(level=logging.INFO)

ALL_POSSIBLE_SECTION_NAMES = [
    "-overview",
    "-reviews",
    "-salaries",
    "-interview-questions",
    "-jobs-cmp",
    "-benefits",
    "-photos",
    "-discussions"
]

def find_company_username(company_name):
    payload = {
        "key": st.secrets["GS_KEY"],
        "q": f"site:ambitionbox.com {company_name}",
        "cx": st.secrets["GS_CX"],
        "start": 1,
        "num": 1
    }
    resp = requests.get("https://customsearch.googleapis.com/customsearch/v1", params=payload)
    resp.raise_for_status()
    resp_json = resp.json()
    resp_links = [i["link"] for i in resp_json.get("items", [])]
    company_link_end = None
    if len(resp_links):
        company_link = resp_links[0]
        company_links_split = company_link.split("/")
        for i in company_links_split:
            for j in ALL_POSSIBLE_SECTION_NAMES:
                if j in i:
                    company_link_end = i.replace(j, "")
                    break
        if isinstance(company_link_end, str):
            return company_link_end
        else:
            return None
    return None

def clean_html(raw_html):
    soup = BeautifulSoup(raw_html, "html.parser")
    return soup.get_text(separator="\n").strip()

session = requests.Session()

headers = {}
headers["User-Agent"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
headers["accept"] = "*/*"
headers["accept-encoding"] = "gzip, deflate, br, zstd"
headers["accept-language"] = "en-GB,en-US;q=0.9,en;q=0.8"
headers["cache-control"] = "no-cache"

resp = session.get('http://www.ambitionbox.com/overview/google-overview', headers=headers)

def find_build_id(response):
    soup = BeautifulSoup(response.text, 'html.parser')
    script_tag = soup.find('script', id="__NEXT_DATA__")
    if script_tag:
        json_data = json.loads(script_tag.string)
        
        build_id = json_data.get('buildId')
        
        if build_id:
            return build_id
        else:
            return None
    else:
        return None
    
BUILD_ID = find_build_id(resp)

def fetch_company_data(company_name, exact_match):
    if exact_match:
        company_username = company_name.lower().replace(" ", "-")
        logging.info(f"company_username: {company_username}")
    else:
        company_username = find_company_username(company_name)
    if company_username is None:
        company_username = company_name.lower().replace(" ", "-")
    """Fetch company data from an external source."""
    AMBITION_BOX_URI = f"https://www.ambitionbox.com/_next/data/{BUILD_ID}/overview/{company_username}-overview.json"
    response = session.get(AMBITION_BOX_URI, headers=headers)
    logging.info(f"response url: {AMBITION_BOX_URI}")
    logging.info(f"response headers: {headers}")
    logging.info(f"response status code: {response.status_code}")
    # logging.info("response: ", response.text)
    data = {}
    if response.status_code == 200:
        response = response.json()
        for k, v in response["pageProps"].items():
            if k in ["companyMetaInformation", "benefits", "companyHeaderData", "interviewsData", "salariesList", "photosData", "jobsData", "faqs", "aggregatedRatingsData", "officeLocations", "similarCompanies","reviews"]:
                data[k] = v
        return data, True
    else:
        return data, False


def display_company_data(data):
    """Display the company data in the Streamlit app."""
    meta_info = data.get('companyMetaInformation', {})
    primaryIndustry = "N/A"
    if meta_info.get("primaryIndustry"):
        primaryIndustry = meta_info.get("primaryIndustry")
        if len(primaryIndustry):
            primaryIndustry = [i["name"] for i in primaryIndustry]
            primaryIndustry = ", ".join(primaryIndustry) if len(primaryIndustry) > 1 else primaryIndustry[0]

    secondaryIndustry = "N/A"
    if meta_info.get("secondaryIndustry"):
        secondaryIndustry = meta_info.get("secondaryIndustry")
        if len(secondaryIndustry):
            secondaryIndustry = [i["name"] for i in secondaryIndustry]
            secondaryIndustry = ", ".join(secondaryIndustry) if len(secondaryIndustry) > 1 else secondaryIndustry[0]

    st.header(f"Company Overview: {meta_info.get('companyName', 'N/A')}")

    # Display basic company info with checks for missing data
    st.markdown(f"""
    - **Name**: {meta_info.get('companyName', 'N/A')}
    - **Description**: {meta_info.get('description', 'N/A')}
    - **Website**: [{meta_info.get('websiteName', 'N/A')}]({meta_info.get('website', '#')})
    - **CEO**: {meta_info.get('ceo', 'N/A')}
    - **Founded Year**: {meta_info.get('foundedYear', 'N/A')}
    - **Global Employee Count**: {meta_info.get('globalEmployeeCount', 'N/A')}
    - **Indian Employee Count**: {meta_info.get('indianEmployeeCountRange', 'N/A')}
    - **Type of Company**: {', '.join([type['name'] for type in meta_info.get('typeOfCompany', [])]) or 'N/A'}
    - **Ownership**: {meta_info.get('ownership', {}).get('name', 'N/A')}
    - **Primary Industries**: {primaryIndustry}
    - **Secondary Industries**: {secondaryIndustry}
    """)

    st.subheader("Social Media Links")
    social_links = meta_info.get('socialLinks', {})
    if social_links:
        for platform, url in social_links.items():
            if url:
                st.markdown(f"- [{platform.capitalize()}]({url})")
    else:
        st.write("No social media links available.")

    # Display company ratings
    st.subheader("Company Ratings")
    ratings_data = data.get('aggregatedRatingsData', {}).get('ratingDistribution', {}).get('data', {}).get('ratings', {})
    if ratings_data:
        st.write(pd.DataFrame.from_dict(ratings_data, orient='index', columns=['Rating']))
    else:
        st.write("No ratings data available.")

    # Interview data
    st.subheader("Interview Insights")
    interview_data = data.get('interviewsData', {})
    if interview_data:
        st.write(f"Total Interview Count: {interview_data.get('interviewRoundsData', {}).get('Meta', {}).get('InterviewCount', 'N/A')}")
        st.write("Interview Duration:")
        st.write(pd.DataFrame(interview_data.get('interviewRoundsData', {}).get('Duration', [])))
        st.write("Difficulty Levels:")
        st.write(pd.DataFrame(interview_data.get('interviewRoundsData', {}).get('Difficulty', [])))
    else:
        st.write("No interview insights available.")

    # Display job details
    st.subheader("Job Listings")
    jobs_data = data.get('jobsData', {}).get('data', {}).get('Jobs', [])
    if jobs_data:
        job_listings = pd.DataFrame(jobs_data)
        st.dataframe(job_listings[['Title', 'Locations', 'MinExp', 'MaxExp', 'Skills', 'PostedOn']], width=700)
    else:
        st.write("No job listings available.")

    # Salary insights
    st.subheader("Salary Insights")
    salaries = data.get('salariesList', {}).get('designations', {}).get('jobProfiles', [])
    if salaries:
        salary_df = pd.DataFrame(salaries)
        st.dataframe(salary_df[['jobProfileName', 'minExperience', 'maxExperience', 'minCtc', 'maxCtc', 'avgCtc']], width=700)
    else:
        st.write("No salary insights available.")

    # Work policy distribution
    st.subheader("Work Policy Distribution")
    work_policy = data.get('aggregatedRatingsData', {}).get('workPolicyDistribution', {}).get('data', {}).get('workPolicyList', [])
    if work_policy:
        st.write(pd.DataFrame(work_policy))
    else:
        st.write("No work policy distribution data available.")

    # Gender insights
    st.subheader("Gender Insights")
    gender_insights = data.get('aggregatedRatingsData', {}).get('genderInsights', {}).get('data', {})
    if gender_insights:
        st.write("Male:")
        st.write(pd.DataFrame(gender_insights.get('M', {}).get('topRatings', [])))
        st.write("Female:")
        st.write(pd.DataFrame(gender_insights.get('F', {}).get('topRatings', [])))
    else:
        st.write("No gender insights available.")

    # Employee benefits
    st.subheader("Employee Benefits")
    benefits = data.get('benefits') or {}
    benefits_list = benefits.get('benefits', []) if isinstance(benefits, dict) else []
    if len(benefits_list):
        st.dataframe(pd.DataFrame(benefits_list)[['name', 'count']], width=500)
    else:
        st.write("No employee benefits data available.")

    # Display office photos
    st.subheader("Company Photos")
    photos = data.get('photosData', {}).get('data', {}).get('Photos', [])
    if photos:
        for photo in photos:
            st.image(photo.get('Url'), caption=photo.get('Caption', ''))
    else:
        st.write("No company photos available.")

    # FAQs section
    st.subheader("Frequently Asked Questions")
    faqs = data.get('faqs', [])
    if faqs:
        for faq in faqs:
            with st.expander(faq.get('question', 'N/A')):
                st.write(clean_html(faq.get('answer', 'N/A')))
    else:
        st.write("No FAQs available.")

    if 'similarCompanies' in data:
        st.subheader("Similar Companies")
        similar_companies = data['similarCompanies']
        for company in similar_companies:
            st.markdown(f"- **{company['shortName']}**: {company['industry']}")



    # Display office locations
    st.subheader("Office Locations")
    office_locations = data.get('officeLocations', [])
    if office_locations:
        for location in office_locations:
            with st.expander(f"{location.get('name', 'N/A')} ({location.get('state', 'N/A')})"):
                st.write(f"**Average Rating:** {location.get('avgCompanyRating', 'N/A')}")
                st.write(f"**Review Count:** {location.get('reviewsCount', 0)}")
                st.write(f"**Salary Count:** {location.get('salariesCount', 0)}")
                
                # Display addresses
                addresses = location.get('addresses', [])
                if addresses:
                    for address in addresses:
                        st.write(f"- **Office Title:** {address.get('officeTitle', 'N/A')}")
                        st.write(f"  **City:** {address.get('city', 'N/A')}")
                        st.write(f"  **Pincode:** {address.get('pincode', 'N/A')}")
                        st.write(f"  **Address:** {address.get('address', 'N/A')}")
                else:
                    st.write("No specific addresses available for this location.")
    else:
        st.write("No office locations available.")


    # Display reviews
    st.subheader("Employee Reviews")
    reviews = data.get('reviews', [])
    if len(reviews):
        for review in reviews:
            with st.expander(f"Review by {review.get('userName', 'Anonymous')} (Rating: {review.get('overallCompanyRating', 'N/A')})"):
                st.write(f"**Likes:** {review.get('likesText', 'N/A')}")
                st.write(f"**Dislikes:** {review.get('disLikesText', 'N/A')}")
                st.write(f"**Work Policy:** {review.get('workPolicy', 'N/A')} - {review.get('workPolicyOther', 'N/A')}")
                # st.write(f"**Job Location:** {review.get('jobLocation', {}).get('name', 'N/A')}")
                st.write(f"**Division:** {review.get('division', 'N/A')}")
                st.write(f"**Employment Type:** {review.get('employmentType', 'N/A')}")
                st.write(f"**Modified:** {review.get('modifiedHumanReadable', 'N/A')}")

                # Display rating distribution
                ratings = review.get('ratingDistribution', [])
                if ratings:
                    st.write("**Rating Distribution:**")
                    ratings_df = pd.DataFrame(ratings)
                    st.dataframe(ratings_df)
                else:
                    st.write("No detailed ratings available.")
    else:
        st.write("No reviews available.")
def main():
    # Load local data for backup (optional)
    # local_data = load_json_data()

    # Streamlit app title
    st.title("Company Overview Finder")

    # Input field for company name
    input_company = st.text_input("Enter the company name:", "")
    
    exact_match = st.checkbox("Exact match", value=False)
    # Button to trigger the search
    if st.button("Search"):
        if input_company:
            logging.info(input_company)
            data, success = fetch_company_data(input_company.strip(), exact_match)

            if success:
                # Display company data if found
                display_company_data(data)
            else:
                st.write("Company not found or data unavailable.")
                # Optional: Display local backup data if needed
                # display_company_data(local_data)
        else:
            st.write("Please enter a company name to search.")
# Run the main function
if __name__ == "__main__":
    main()
