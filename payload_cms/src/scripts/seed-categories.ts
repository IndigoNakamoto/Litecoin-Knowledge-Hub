import { getPayload } from 'payload'
import config from '../payload.config'

// Helper function to create description
function createDescription(text: string) {
  return text
}

async function seedCategories() {
  const payload = await getPayload({ config })

  console.log('🌱 Seeding categories...')

  // Main categories with their descriptions
  const mainCategories = [
    {
      name: '🏛️ Litecoin Foundations (Getting Started)',
      icon: '🏛️',
      order: 1,
      audienceLevel: 'beginner' as const,
      description: 'Basic introductory content for newcomers. Cover fundamental concepts like what Litecoin is, how it differs from Bitcoin, basic wallet concepts, and simple getting started guides.',
    },
    {
      name: '💸 Acquiring & Managing LTC',
      icon: '💸',
      order: 2,
      audienceLevel: 'beginner' as const,
      description: 'Guides for buying, selling, and managing Litecoin. Includes exchanges, wallets, trading basics, and financial management strategies.',
    },
    {
      name: '🔒 Wallets & Security',
      icon: '🔒',
      order: 3,
      audienceLevel: 'beginner' as const,
      description: 'Wallet setup, security best practices, backup strategies, and protection against scams. Essential knowledge for safely storing Litecoin.',
    },
    {
      name: '🛠️ Using Litecoin (Transactions & Features)',
      icon: '🛠️',
      order: 4,
      audienceLevel: 'intermediate' as const,
      description: 'How to send and receive Litecoin, understand transactions, use advanced features like MWEB privacy, and accept LTC for business.',
    },
    {
      name: '⚙️ Technical Deep Dive',
      icon: '⚙️',
      order: 5,
      audienceLevel: 'advanced' as const,
      description: 'Technical details about Litecoin\'s protocol, mining, network infrastructure, and advanced features. For developers and technical users.',
    },
    {
      name: '⛏️ Mining',
      icon: '⛏️',
      order: 6,
      audienceLevel: 'intermediate' as const,
      description: 'Mining Litecoin, hardware requirements, pool mining, profitability calculations, and mining economics.',
    },
    {
      name: '🌳 Ecosystem & Community',
      icon: '🌳',
      order: 7,
      audienceLevel: 'intermediate' as const,
      description: 'Litecoin Foundation, development projects, community resources, events, and ecosystem growth initiatives.',
    },
    {
      name: '❓ FAQs & Troubleshooting',
      icon: '❓',
      order: 8,
      audienceLevel: 'beginner' as const,
      description: 'Common questions, troubleshooting guides, and solutions to frequently encountered problems with Litecoin.',
    },
  ]

  // Create main categories first
  const createdMainCategories = []
  for (const categoryData of mainCategories) {
    try {
      const category = await payload.create({
        collection: 'categories',
        data: categoryData,
      })
      createdMainCategories.push(category)
      console.log(`✅ Created main category: ${category.name}`)
    } catch (error) {
      console.error(`❌ Failed to create category ${categoryData.name}:`, error)
    }
  }

  // Subcategories organized by parent
  const subCategories = [
    // Litecoin Foundations subcategories
    {
      parentName: '🏛️ Litecoin Foundations (Getting Started)',
      categories: [
        { name: 'Core Concepts', order: 1, description: 'Fundamental Litecoin concepts: what is LTC, cryptocurrency basics, blockchain technology, P2P networks, decentralization' },
        { name: 'History & Purpose', order: 2, description: 'Litecoin\'s history, Charlie Lee, "Digital Silver" positioning, mission and value proposition' },
        { name: 'Key Comparisons', order: 3, description: 'LTC vs Bitcoin, LTC vs Ethereum, LTC vs fiat currency comparisons and analysis' },
        { name: 'Economics & Tokenomics', order: 4, description: 'Total supply, halving mechanics, block rewards, issuance schedule, store of value properties' },
      ]
    },
    // Acquiring & Managing LTC subcategories
    {
      parentName: '� Acquiring & Managing LTC',
      categories: [
        { name: 'How to Buy', order: 1, description: 'Credit card purchases, bank transfers, exchange buying, P2P purchasing methods' },
        { name: 'How to Sell', order: 2, description: 'Selling on exchanges, cashing out to fiat, selling strategies' },
        { name: 'Exchanges & Platforms', order: 3, description: 'CEX vs DEX, brokers, apps, platform comparisons and reviews' },
        { name: 'Trading & Speculation', order: 4, description: 'Market analysis, price charts, trading pairs, trading strategies' },
      ]
    },
    // Wallets & Security subcategories
    {
      parentName: '🔒 Wallets & Security',
      categories: [
        { name: 'Wallet Basics', order: 1, description: 'What wallets are, public/private keys, seed phrases, hot vs cold wallets, custodial vs non-custodial' },
        { name: 'Wallet Types', order: 2, description: 'Hardware wallets, software wallets, Litewallet, paper wallets, multisig solutions' },
        { name: 'Security Best Practices', order: 3, description: 'Backup strategies, scam avoidance, phishing protection, 2FA, key security' },
        { name: 'Wallet Setup & Use', order: 4, description: 'Creating wallets, restoring from seed, hardware setup guides, wallet management' },
      ]
    },
    // Using Litecoin subcategories
    {
      parentName: '🛠️ Using Litecoin (Transactions & Features)',
      categories: [
        { name: 'Sending & Receiving', order: 1, description: 'How to send LTC, receiving payments, address formats, QR codes, transaction monitoring' },
        { name: 'Transaction Details', order: 2, description: 'Fees, confirmation times, 0-conf transactions, stuck transaction troubleshooting' },
        { name: 'Privacy (MWEB)', order: 3, description: 'MWEB technology, confidential transactions, privacy features, MWEB vs standard transactions' },
        { name: 'Merchant & Business Use', order: 4, description: 'Accepting LTC payments, payment processors, Litecoin Card, merchant adoption' },
      ]
    },
    // Technical Deep Dive subcategories
    {
      parentName: '⚙️ Technical Deep Dive',
      categories: [
        { name: 'Core Protocol', order: 1, description: 'PoW consensus, Scrypt algorithm, SegWit, transaction malleability, block structure' },
        { name: 'Network & Infrastructure', order: 2, description: 'Running nodes, hardware requirements, Litecoin Core, mainnet/testnet, explorers' },
        { name: 'Advanced Topics', order: 3, description: 'Address types, LIPs, dust limits, DNS seeds, checkpoints, magic numbers' },
      ]
    },
    // Mining subcategories
    {
      parentName: '⛏️ Mining',
      categories: [
        { name: 'Mining Basics', order: 1, description: 'What is mining, why mine LTC, Scrypt vs SHA-256, mining rewards and security' },
        { name: 'Mining Hardware', order: 2, description: 'ASIC miners, GPUs, recommended hardware, Antminer L-series' },
        { name: 'How to Mine (Setup Guides)', order: 3, description: 'Solo vs pool mining, joining pools, mining software, profitability calculations' },
      ]
    },
    // Ecosystem & Community subcategories
    {
      parentName: '🌳 Ecosystem & Community',
      categories: [
        { name: 'Key Organizations', order: 1, description: 'Litecoin Foundation, development team, Charlie Lee\'s role, governance' },
        { name: 'Development & Projects', order: 2, description: 'Core development, Lightning Network, Ordinals, OmniLite, open source contributions' },
        { name: 'Community & Resources', order: 3, description: 'Official channels, forums, contribution guides, Litecoin Summit events' },
      ]
    },
    // FAQs & Troubleshooting subcategories
    {
      parentName: '❓ FAQs & Troubleshooting',
      categories: [
        { name: 'Common User Questions', order: 1, description: 'Investment questions, fee concerns, transaction times, wallet recommendations' },
        { name: 'Problem Solving', order: 2, description: 'Stuck transactions, lost seeds, wrong addresses, wallet sync issues' },
      ]
    },
  ]

  // Create subcategories
  for (const parentGroup of subCategories) {
    const parentCategory = createdMainCategories.find(cat => cat.name === parentGroup.parentName)
    if (!parentCategory) {
      console.error(`❌ Parent category not found: ${parentGroup.parentName}`)
      continue
    }

    for (const subCategoryData of parentGroup.categories) {
      try {
        const subCategory = await payload.create({
          collection: 'categories',
          data: {
            name: subCategoryData.name,
            order: subCategoryData.order,
            audienceLevel: 'beginner' as const,
            description: subCategoryData.description,
            parent: parentCategory.id,
          },
        })
        console.log(`✅ Created subcategory: ${subCategory.name} (under ${parentGroup.parentName})`)
      } catch (error) {
        console.error(`❌ Failed to create subcategory ${subCategoryData.name}:`, error)
      }
    }
  }

  console.log('🎉 Category seeding completed!')
}

// Run the seed function
seedCategories()
  .then(() => {
    console.log('✅ Seeding completed successfully')
    process.exit(0)
  })
  .catch((error) => {
    console.error('❌ Seeding failed:', error)
    process.exit(1)
  })

export default seedCategories
