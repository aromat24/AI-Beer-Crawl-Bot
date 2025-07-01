# AI Beer Crawl App

A comprehensive social networking platform that connects like-minded individuals for organized bar hopping experiences. Built with Flask, React, and n8n automation.

## 🍺 Features

- **Intelligent Group Matching**: AI-powered matching based on location, demographics, and preferences
- **WhatsApp Integration**: Seamless communication through WhatsApp Business API
- **Real-time Coordination**: Live updates for group activities and venue changes
- **Automated Scheduling**: Smart scheduling and venue selection
- **Safety Features**: Group monitoring and emergency protocols
- **Venue Partnership**: Integration with local bars and restaurants

## 🏗️ Architecture

- **Backend**: Flask API with SQLAlchemy ORM
- **Frontend**: React with Tailwind CSS and shadcn/ui
- **Automation**: n8n workflow for WhatsApp integration
- **Database**: SQLite (development) / PostgreSQL (production)

## 🚀 Quick Start

### Backend Setup
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
python src/main.py
```

### Frontend Setup
```bash
cd frontend
pnpm install
pnpm run dev --host
```

### n8n Workflow
1. Import `n8n/ai_beer_crawl_workflow.json` into your n8n instance
2. Configure WhatsApp webhook endpoints
3. Update API base URLs in workflow configuration
4. Activate the workflow

## 📱 Usage

1. **User Registration**: Send WhatsApp message expressing interest in beer crawling
2. **Group Formation**: System matches users based on preferences and location
3. **Group Activation**: When 5+ members join, group becomes active
4. **Bar Crawling**: Automated venue selection and coordination
5. **Session Management**: Real-time updates and group communication

## 🔧 API Endpoints

### User Management
- `POST /api/beer-crawl/signup` - Register new user
- `POST /api/beer-crawl/find-group` - Find or create group

### Group Management
- `POST /api/beer-crawl/groups/{id}/start` - Start group session
- `POST /api/beer-crawl/groups/{id}/next-bar` - Move to next venue
- `GET /api/beer-crawl/groups/{id}/status` - Get group status

### Venue Management
- `GET /api/beer-crawl/bars` - List available bars
- `POST /api/beer-crawl/bars` - Add new bar (for owners)

## 🗄️ Database Schema

- **UserPreferences**: User profiles and matching preferences
- **Bar**: Venue information and location data
- **CrawlGroup**: Group formation and session management
- **GroupMember**: User-group relationships
- **CrawlSession**: Individual venue visits and timing

## 🔒 Security Features

- HTTPS encryption for all communications
- WhatsApp end-to-end encryption
- Data minimization and privacy controls
- Rate limiting and abuse prevention
- User safety protocols and reporting

## 📈 Business Model

- **Free Tier**: Basic group matching and coordination
- **Premium Features**: Priority matching and exclusive venues
- **Venue Partnerships**: Revenue sharing with participating bars
- **Corporate Events**: B2B event coordination services

## 🌟 Future Enhancements

- Mobile applications (iOS/Android)
- Machine learning for improved matching
- Augmented reality venue discovery
- Multi-city expansion
- Blockchain-based reputation system

## 📄 Documentation

See `documentation.md` for comprehensive technical documentation including:
- Detailed API specifications
- Frontend component architecture
- n8n workflow documentation
- Deployment guides
- Security considerations

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📧 Support

For technical support and implementation assistance, please refer to the comprehensive documentation or contact the development team.

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Built with ❤️ by Manus AI**

