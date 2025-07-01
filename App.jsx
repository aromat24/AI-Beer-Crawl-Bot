import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button.jsx'
import { Input } from '@/components/ui/input.jsx'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card.jsx'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select.jsx'
import { Badge } from '@/components/ui/badge.jsx'
import { Separator } from '@/components/ui/separator.jsx'
import { Beer, Users, MapPin, Clock, Phone, CheckCircle } from 'lucide-react'
import './App.css'

const API_BASE = '/api/beer-crawl'

function App() {
  const [currentStep, setCurrentStep] = useState('signup') // signup, waiting, active, completed
  const [userData, setUserData] = useState({
    whatsapp_number: '',
    preferred_area: '',
    preferred_group_type: '',
    gender: '',
    age_range: ''
  })
  const [groupData, setGroupData] = useState(null)
  const [sessionData, setSessionData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const areas = [
    'northern quarter',
    'city centre', 
    'deansgate',
    'ancoats',
    'spinningfields'
  ]

  const groupTypes = [
    'mixed',
    'male',
    'female',
    'straight',
    'bi',
    'lgbtq+'
  ]

  const genders = ['male', 'female', 'non-binary', 'prefer not to say']
  const ageRanges = ['18-25', '26-35', '36-45', '46+']

  const handleSignup = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      const response = await fetch(`${API_BASE}/signup`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(userData),
      })

      const data = await response.json()

      if (response.ok) {
        setCurrentStep('waiting')
        findGroup()
      } else {
        setError(data.error || 'Signup failed')
      }
    } catch (err) {
      setError('Network error. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const findGroup = async () => {
    setLoading(true)
    try {
      const response = await fetch(`${API_BASE}/find-group`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ whatsapp_number: userData.whatsapp_number }),
      })

      const data = await response.json()

      if (response.ok) {
        setGroupData(data.group)
        if (data.ready_to_start) {
          setCurrentStep('ready')
        }
      } else {
        setError(data.error || 'Failed to find group')
      }
    } catch (err) {
      setError('Network error. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const startGroup = async () => {
    if (!groupData) return
    
    setLoading(true)
    try {
      const response = await fetch(`${API_BASE}/groups/${groupData.id}/start`, {
        method: 'POST',
      })

      const data = await response.json()

      if (response.ok) {
        setSessionData(data)
        setCurrentStep('active')
      } else {
        setError(data.error || 'Failed to start group')
      }
    } catch (err) {
      setError('Network error. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const nextBar = async () => {
    if (!groupData) return
    
    setLoading(true)
    try {
      const response = await fetch(`${API_BASE}/groups/${groupData.id}/next-bar`, {
        method: 'POST',
      })

      const data = await response.json()

      if (response.ok) {
        setSessionData(data)
      } else {
        setError(data.error || 'Failed to get next bar')
      }
    } catch (err) {
      setError('Network error. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const SignupForm = () => (
    <Card className="w-full max-w-md mx-auto">
      <CardHeader className="text-center">
        <div className="flex justify-center mb-4">
          <Beer className="h-12 w-12 text-amber-500" />
        </div>
        <CardTitle className="text-2xl">Join AI Beer Crawl</CardTitle>
        <CardDescription>
          Find your perfect drinking group and explore the best bars in Manchester
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSignup} className="space-y-4">
          <div>
            <label className="text-sm font-medium">WhatsApp Number</label>
            <Input
              type="tel"
              placeholder="+44 7XXX XXXXXX"
              value={userData.whatsapp_number}
              onChange={(e) => setUserData({...userData, whatsapp_number: e.target.value})}
              required
            />
          </div>

          <div>
            <label className="text-sm font-medium">Preferred Area</label>
            <Select onValueChange={(value) => setUserData({...userData, preferred_area: value})}>
              <SelectTrigger>
                <SelectValue placeholder="Select area" />
              </SelectTrigger>
              <SelectContent>
                {areas.map(area => (
                  <SelectItem key={area} value={area}>{area}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <label className="text-sm font-medium">Group Type</label>
            <Select onValueChange={(value) => setUserData({...userData, preferred_group_type: value})}>
              <SelectTrigger>
                <SelectValue placeholder="Select group type" />
              </SelectTrigger>
              <SelectContent>
                {groupTypes.map(type => (
                  <SelectItem key={type} value={type}>{type}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <label className="text-sm font-medium">Gender</label>
            <Select onValueChange={(value) => setUserData({...userData, gender: value})}>
              <SelectTrigger>
                <SelectValue placeholder="Select gender" />
              </SelectTrigger>
              <SelectContent>
                {genders.map(gender => (
                  <SelectItem key={gender} value={gender}>{gender}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <label className="text-sm font-medium">Age Range</label>
            <Select onValueChange={(value) => setUserData({...userData, age_range: value})}>
              <SelectTrigger>
                <SelectValue placeholder="Select age range" />
              </SelectTrigger>
              <SelectContent>
                {ageRanges.map(range => (
                  <SelectItem key={range} value={range}>{range}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {error && (
            <div className="text-red-500 text-sm">{error}</div>
          )}

          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? 'Finding Your Group...' : 'Join Beer Crawl'}
          </Button>
        </form>
      </CardContent>
    </Card>
  )

  const WaitingScreen = () => (
    <Card className="w-full max-w-md mx-auto">
      <CardHeader className="text-center">
        <Users className="h-12 w-12 text-blue-500 mx-auto mb-4" />
        <CardTitle>Finding Your Group</CardTitle>
        <CardDescription>
          We're matching you with like-minded people in {userData.preferred_area}
        </CardDescription>
      </CardHeader>
      <CardContent className="text-center">
        {groupData && (
          <div className="space-y-4">
            <div className="flex items-center justify-center space-x-2">
              <Badge variant="secondary">
                {groupData.current_members}/10 members
              </Badge>
              <Badge variant="outline">
                {groupData.group_type}
              </Badge>
            </div>
            
            <div className="text-sm text-muted-foreground">
              {groupData.current_members < 2 
                ? `Need ${2 - groupData.current_members} more people to start`
                : 'Ready to start! Waiting for confirmation...'
              }
            </div>

            {groupData.current_members >= 2 && (
              <Button onClick={startGroup} disabled={loading} className="w-full">
                {loading ? 'Starting...' : 'Start Beer Crawl!'}
              </Button>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )

  const ActiveSession = () => (
    <Card className="w-full max-w-md mx-auto">
      <CardHeader className="text-center">
        <MapPin className="h-12 w-12 text-green-500 mx-auto mb-4" />
        <CardTitle>Your Beer Crawl is Active!</CardTitle>
        <CardDescription>
          Group of {groupData?.current_members} people
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {sessionData && (
          <>
            <div className="text-center">
              <h3 className="font-semibold text-lg">{sessionData.first_bar?.name || sessionData.bar?.name}</h3>
              <p className="text-sm text-muted-foreground">{sessionData.first_bar?.address || sessionData.bar?.address}</p>
            </div>

            <Separator />

            <div className="flex items-center space-x-2">
              <Clock className="h-4 w-4" />
              <span className="text-sm">
                Meeting time: {new Date(sessionData.meeting_time).toLocaleTimeString()}
              </span>
            </div>

            <Button 
              onClick={() => window.open(sessionData.map_link, '_blank')} 
              className="w-full"
              variant="outline"
            >
              <MapPin className="h-4 w-4 mr-2" />
              Open in Maps
            </Button>

            <Button onClick={nextBar} disabled={loading} className="w-full">
              {loading ? 'Finding Next Bar...' : 'Next Bar'}
            </Button>

            <div className="text-xs text-center text-muted-foreground">
              The group will automatically end at midnight
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )

  return (
    <div className="min-h-screen bg-gradient-to-br from-amber-50 to-orange-100 p-4 flex items-center justify-center">
      <div className="w-full max-w-4xl">
        {currentStep === 'signup' && <SignupForm />}
        {(currentStep === 'waiting' || currentStep === 'ready') && <WaitingScreen />}
        {currentStep === 'active' && <ActiveSession />}
        
        {/* Footer */}
        <div className="text-center mt-8 text-sm text-muted-foreground">
          <p>Free for all users • Premium features for bar owners</p>
        </div>
      </div>
    </div>
  )
}

export default App

