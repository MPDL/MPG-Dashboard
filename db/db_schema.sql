--
-- PostgreSQL database dump
--

-- Dumped from database version 17rc1
-- Dumped by pg_dump version 17rc1

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: open_data_type; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.open_data_type AS ENUM (
    'yes',
    'no',
    'partial'
);


ALTER TYPE public.open_data_type OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: publication_pdf_urls; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.publication_pdf_urls (
    pdf_url_id character varying NOT NULL,
    pure_id character varying NOT NULL,
    pdf_url character varying,
    locator_url character varying,
    pure_content_category character varying,
    openalex_version character varying,
    pure_oa_status character varying,
    openalex_oa character varying,
    url_source character varying
);


ALTER TABLE public.publication_pdf_urls OWNER TO postgres;

--
-- Name: publications; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.publications (
    pure_title character varying,
    openalex_title character varying,
    pure_id character varying NOT NULL,
    openalex_id character varying,
    doi character varying,
    pure_oa_status character varying,
    openalex_oa_status character varying,
    openalex_oa character varying,
    manual_download boolean,  
    discoverable boolean,
    pure_genre character varying,
    openalex_type character varying,
    crossref_type character varying,
    publication_year character varying,
    publication_date character varying,
    publisher character varying,
    open_data public.open_data_type,
    software_used character varying,
    software_shared character varying,
    software_created character varying,
    data_mentioned character varying,
    data_shared character varying
);


ALTER TABLE public.publications OWNER TO postgres;

--
-- Data for Name: publication_pdf_urls; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.publication_pdf_urls (pdf_url_id, pure_id, pdf_url, locator_url, pure_content_category, openalex_version, pure_oa_status, openalex_oa, url_source) FROM stdin;
\.


--
-- Data for Name: publications; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.publications (pure_title, openalex_title, pure_id, openalex_id, doi, pure_oa_status, openalex_oa_status, openalex_oa, manual_download, discoverable, pure_genre, openalex_type, crossref_type, publication_year, publication_date, publisher, open_data, software_used, software_shared, software_created, data_mentioned, data_shared) FROM stdin;
\.


--
-- Name: publications publications_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.publications
    ADD CONSTRAINT publications_pkey PRIMARY KEY (pure_id);


--
-- Name: publication_pdf_urls publication_pdf_urls_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.publication_pdf_urls
    ADD CONSTRAINT publication_pdf_urls_pkey PRIMARY KEY (pdf_url_id);


--
-- PostgreSQL database dump complete
--

