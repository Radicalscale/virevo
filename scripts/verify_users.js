const { MongoClient } = require('mongodb');

const SOURCE_URI = 'mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada';
const DEST_URI = 'mongodb://mongo:VvAstqnjLZVbnVPfmaOERekKMOdwlGaX@gondola.proxy.rlwy.net:43413';

async function verify() {
    const sourceClient = new MongoClient(SOURCE_URI);
    const destClient = new MongoClient(DEST_URI);

    try {
        await sourceClient.connect();
        const sourceDb = sourceClient.db('test_database');
        const sourceCount = await sourceDb.collection('users').countDocuments();
        const sourceUser = await sourceDb.collection('users').findOne({ email: 'kendrickbowman9@gmail.com' });

        console.log('--- SOURCE DB ---');
        console.log(`Total Users: ${sourceCount}`);
        console.log(`User 'kendrickbowman9@gmail.com' found: ${!!sourceUser}`);
        if (sourceUser) console.log(`  - ID: ${sourceUser._id}`);

        await destClient.connect();
        const destDb = destClient.db('virevo');
        const destCount = await destDb.collection('users').countDocuments();
        const destUser = await destDb.collection('users').findOne({ email: 'kendrickbowman9@gmail.com' });

        console.log('\n--- DESTINATION DB ---');
        console.log(`Total Users: ${destCount}`);
        console.log(`User 'kendrickbowman9@gmail.com' found: ${!!destUser}`);

    } catch (err) {
        console.error(err);
    } finally {
        await sourceClient.close();
        await destClient.close();
    }
}

verify();
