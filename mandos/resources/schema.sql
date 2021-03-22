
create table resources(
    id int primary key,
    name varchar not null,
    version varchar,
    via varchar,
    source varchar
);
create table commands(
    id int primary key,
    name varchar not null,
    resource int not null
);
create table compounds(
    id int primary key,
    inchi varchar not null,
    inchikey varchar not null unique,
    smiles varchar not null unique,
    asof datetime not null
);
create table subjects(
    id int primary key,
    marker varchar not null unique,
    name varchar not null unique,
    compound int not null,
    ref int not null,
    asof datetime not null
);
create table objects(
    id int primary key,
    marker varchar not null unique,
    name varchar not null unique,
    ref int not null,
    asof datetime not null
);
create table predicates(
    id int primary key,
    marker varchar not null unique,
    name varchar not null unique,
    ref int not null,
    asof datetime not null
);
create table triples(
    id int primary key,
    marker varchar not null unique,
    subject int not null,
    predicate int not null,
    object int not null,
    subject_text varchar not null,
    object_text varchar not null,
    asof datetime not null
);
create table compound_tags(
    id int primary key,
    marker varchar not null unique,
    ref int not null,
    subject int not null,
    name varchar not null,
    value varchar not null,
    asof datetime not null
);
create table object_tags(
    id int primary key,
    marker varchar not null unique,
    ref int not null,
    object int not null,
    name varchar not null,
    value varchar not null,
    asof datetime not null
);
create table triple_tags(
    id int primary key,
    marker varchar not null unique,
    ref int not null,
    triple int not null,
    name varchar not null,
    value varchar not null,
    asof datetime not null
);
create table queries(
    id int primary key,
    marker varchar not null,
    mandos_version varchar not null,
    value varchar not null,
    address varchar not null,
    dt_input datetime not null,
    dt_chembl_fetched datetime null,
    dt_pubchem_fetched datetime null,
    dt_output datetime null
);
create table query_args(
    id int primary key,
    name varchar not null,
    value varchar not null,
    query int not null
);
create table input_compounds(
    id int primary key,
    value varchar not null,
    query int not null,
    cleaned int not null,
    cleaning_method varchar
);
create table output_data(
    id int primary key,
    value varchar not null,
    kind varchar not null,
    query int not null
);
